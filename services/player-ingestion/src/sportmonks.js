"use strict";

const axios = require("axios");
const config = require("./config");
const { deriveAttributes, normalizePosition } = require("./footballAttributes");
const logger = require("./logger");
const { mapPlayerUpdate } = require("./matchInfluence");

function cleanText(value) {
  if (value === undefined || value === null) {
    return null;
  }
  const text = String(value).trim();
  return text || null;
}

function ageFromDate(value) {
  const raw = cleanText(value);
  if (!raw) {
    return null;
  }
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  const now = new Date();
  let age = now.getUTCFullYear() - date.getUTCFullYear();
  const monthDelta = now.getUTCMonth() - date.getUTCMonth();
  if (monthDelta < 0 || (monthDelta === 0 && now.getUTCDate() < date.getUTCDate())) {
    age -= 1;
  }
  return age;
}

class SportmonksClient {
  constructor() {
    this.client = axios.create({
      baseURL: config.sportmonks.baseUrl,
      timeout: config.sportmonks.timeoutMs,
    });
    this.lastRequestAt = 0;
  }

  async request(path, params = {}) {
    await this.waitForRateLimit();
    const response = await this.client.get(path, {
      params: {
        ...params,
        api_token: config.sportmonks.apiToken,
      },
    });
    return response.data || {};
  }

  async waitForRateLimit() {
    const delayMs = config.sportmonks.rateLimitMs;
    const elapsed = Date.now() - this.lastRequestAt;
    if (delayMs > 0 && elapsed < delayMs) {
      await new Promise((resolve) => {
        setTimeout(resolve, delayMs - elapsed);
      });
    }
    this.lastRequestAt = Date.now();
  }

  async paginate(path, params = {}) {
    const items = [];
    let page = 1;
    for (;;) {
      const payload = await this.request(path, {
        ...params,
        page,
        per_page: config.sportmonks.pageSize,
      });
      items.push(...(payload.data || []));
      const pagination = payload.pagination || {};
      if (!pagination.has_more) {
        return items;
      }
      page += 1;
    }
  }

  async fetchLeagues() {
    if (config.sportmonks.leagueIds.length > 0) {
      return config.sportmonks.leagueIds.map((id) => ({ id: Number(id) }));
    }
    return this.paginate("/leagues", { include: "currentseason" });
  }

  async fetchLeagueDetail(leagueId) {
    const payload = await this.request(`/leagues/${leagueId}`, { include: "currentseason" });
    return payload.data || {};
  }

  async fetchTeamsForLeague(leagueId, seasonId = null) {
    const resolvedSeasonId = seasonId || (await this.resolveSeasonId(leagueId));
    if (!resolvedSeasonId) {
      logger.warn("league has no current season; team sync skipped", { leagueId });
      return [];
    }
    const payload = await this.request(`/teams/seasons/${resolvedSeasonId}`, {
      include: "country;venue",
    });
    return (payload.data || []).map((team) => ({
      id: Number(team.id),
      name: cleanText(team.name || team.display_name),
      leagueId: Number(leagueId),
      seasonId: Number(resolvedSeasonId),
    }));
  }

  async fetchPlayersForTeam(teamId) {
    const payload = await this.request(`/squads/teams/${teamId}`, {
      include: "player.country;player.nationality;player.city;position;detailedPosition",
    });
    return (payload.data || []).map((item) => normalizeSquadPlayer(item, teamId));
  }

  async fetchPlayerById(playerId) {
    const payload = await this.request(`/players/${playerId}`, {
      include: "country;nationality;position;detailedPosition;teams.team",
    });
    if (!payload.data) {
      return null;
    }
    return normalizePlayer(payload.data);
  }

  async fetchUpdatedPlayersSince(since) {
    if (!config.sportmonks.updatedSinceSupported || !since) {
      return [];
    }
    const items = await this.paginate("/players", {
      filters: `updated_since:${new Date(since).toISOString()}`,
      include: "country;nationality;position;detailedPosition;teams.team",
    });
    return items.map((item) => normalizePlayer(item));
  }

  async resolveSeasonId(leagueId) {
    const league = await this.fetchLeagueDetail(leagueId);
    const currentSeason = league.currentseason || league.currentSeason || {};
    return currentSeason.id || league.current_season_id || league.currentSeasonId || null;
  }
}

function normalizeSquadPlayer(item, teamId) {
  const player = item.player || item;
  const normalized = normalizePlayer({
    ...player,
    raw: {
      player,
      squad: item,
    },
  });
  return {
    ...normalized,
    teamId: Number(teamId),
  };
}

function normalizePlayer(player) {
  const nationality = player.nationality || player.country || {};
  const position = player.detailedposition || player.detailedPosition || player.position || {};
  const dateOfBirth = player.date_of_birth || player.dateOfBirth || player.birthdate;
  const id = Number(player.id);
  const raw = player.raw || player;
  const matchUpdate = mapPlayerUpdate({
    ...player,
    playerId: id,
    raw,
  });
  const normalized = {
    playerId: id,
    name:
      cleanText(player.display_name || player.displayName || player.name || player.common_name) ||
      "Unknown Player",
    nationality: cleanText(nationality.name || player.nationality || player.country),
    age: Number(player.age) || ageFromDate(dateOfBirth),
    position: normalizePosition(position.name || player.position_name || player.position),
    sportmonksImageUrl: cleanText(player.image_path || player.imagePath || player.photo_url),
    isRegen: false,
    sourceProvider: "sportmonks",
    minutesPlayed: matchUpdate.minutes,
    lastMatchRating: matchUpdate.rating,
    isInjured: matchUpdate.injured,
    injuryReturnDate: matchUpdate.injuryReturnDate,
    raw,
  };
  return {
    ...normalized,
    ...deriveAttributes(normalized),
  };
}

module.exports = {
  SportmonksClient,
  normalizePlayer,
};
