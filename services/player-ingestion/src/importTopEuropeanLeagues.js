"use strict";

const db = require("./db");
const { stableHash } = require("./hash");
const { resolvePlayerImage } = require("./imageResolver");
const logger = require("./logger");
const repository = require("./repository");
const { SportmonksClient } = require("./sportmonks");

const TOP_EUROPEAN_LEAGUES = [
  {
    code: "premier-league",
    leagueId: 8,
    name: "Premier League",
    country: "England",
  },
  {
    code: "la-liga",
    leagueId: 564,
    name: "La Liga",
    country: "Spain",
  },
  {
    code: "bundesliga",
    leagueId: 82,
    name: "Bundesliga",
    country: "Germany",
  },
  {
    code: "serie-a",
    leagueId: 384,
    name: "Serie A",
    country: "Italy",
  },
  {
    code: "ligue-1",
    leagueId: 301,
    name: "Ligue 1",
    country: "France",
  },
  {
    code: "eredivisie",
    leagueId: 72,
    name: "Eredivisie",
    country: "Netherlands",
  },
  {
    code: "liga-portugal",
    leagueId: 462,
    name: "Liga Portugal",
    country: "Portugal",
  },
];

function envBool(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || String(raw).trim() === "") {
    return fallback;
  }
  return ["1", "true", "yes", "y", "on"].includes(String(raw).trim().toLowerCase());
}

function envInt(name, fallback, minimum = 0) {
  const raw = process.env[name];
  const parsed = raw === undefined ? fallback : Number.parseInt(String(raw), 10);
  if (!Number.isFinite(parsed) || parsed < minimum) {
    return fallback;
  }
  return parsed;
}

function selectedLeagues() {
  const requested = (process.env.TOP_EUROPEAN_LEAGUE_IDS || "")
    .split(",")
    .map((item) => Number.parseInt(item.trim(), 10))
    .filter((item) => Number.isFinite(item) && item > 0);
  if (!requested.length) {
    return TOP_EUROPEAN_LEAGUES;
  }
  const requestedSet = new Set(requested);
  return TOP_EUROPEAN_LEAGUES.filter((league) => requestedSet.has(league.leagueId));
}

function withSourceHash(player) {
  return {
    ...player,
    sourceHash:
      player.sourceHash ||
      stableHash({
        playerId: player.playerId,
        name: player.name,
        nationality: player.nationality,
        age: player.age,
        sportmonksImageUrl: player.sportmonksImageUrl,
        leagueId: player.leagueId,
        teamId: player.teamId,
        isRegen: player.isRegen,
        position: player.position,
        overall: player.overall,
        potential: player.potential,
        pace: player.pace,
        shooting: player.shooting,
        passing: player.passing,
        dribbling: player.dribbling,
        defending: player.defending,
        physical: player.physical,
        traits: player.traits,
        personality: player.personality,
      }),
  };
}

function isReusableImageUrl(value) {
  if (!value) {
    return false;
  }
  const text = String(value);
  return text.startsWith("https://res.cloudinary.com/") || text.includes("/image/upload/");
}

async function existingAppPlayerImage(playerId) {
  const result = await db.query(
    `
      SELECT ip.id AS app_player_id, ipim.source_url, ipim.storage_key
      FROM ingestion_players ip
      LEFT JOIN ingestion_player_image_metadata ipim
        ON ipim.player_id = ip.id
       AND ipim.image_role = 'portrait'
       AND ipim.moderation_status = 'approved'
       AND ipim.rights_cleared IS TRUE
      WHERE ip.source_provider = 'sportmonks'
        AND ip.provider_external_id = $1
      LIMIT 1
    `,
    [String(playerId)],
  );
  return result.rows[0] || null;
}

function storeSportmonksPortrait(player, existing) {
  if (existing?.storage_key) {
    return {
      imageUrl: existing.source_url || null,
      storageKey: existing.storage_key,
      imageSource: "cloudinary_derived",
      rightsCleared: true,
      reused: true,
    };
  }
  return { ...resolvePlayerImage(player), reused: false };
}

async function importPlayer(player, context, report) {
  const normalized = withSourceHash({
    ...player,
    leagueId: context.leagueId,
    teamId: context.teamId,
    sourceProvider: "sportmonks",
    isRegen: false,
  });
  const existingAppImage = await existingAppPlayerImage(normalized.playerId);
  let portrait;
  try {
    portrait = await storeSportmonksPortrait(normalized, existingAppImage);
  } catch (error) {
    report.imageFailures += 1;
    logger.warn("top league portrait upload failed", {
      event: "top_league_portrait_failed",
      playerId: normalized.playerId,
      leagueId: context.leagueId,
      teamId: context.teamId,
      reason: error.message,
    });
    return;
  }
  if (!portrait.imageUrl || !portrait.rightsCleared) {
    report.playersSkippedNoImage += 1;
    return;
  }
  await repository.upsertPlayer({
    ...normalized,
    imageUrl: portrait.imageUrl,
    imageSource: portrait.imageSource,
    rightsCleared: portrait.rightsCleared,
  });
  const appPlayerId =
    existingAppImage?.app_player_id || (await repository.upsertAppPlayerMirror(normalized));
  await repository.upsertAppPlayerImageMetadata({
    appPlayerId,
    playerId: normalized.playerId,
    imageUrl: portrait.imageUrl,
    storageKey: portrait.storageKey,
    rightsCleared: portrait.rightsCleared,
  });
  await repository.recalculateTeamStrength(context.teamId);
  report.playersImported += 1;
  if (portrait.reused) {
    report.imagesReused += 1;
  } else {
    report.imagesUploaded += 1;
  }
  logger.info("top league player imported", {
    event: "top_league_player_imported",
    playerId: normalized.playerId,
    leagueId: context.leagueId,
    teamId: context.teamId,
    hasImage: true,
  });
}

async function importLeague(client, league, options, report) {
  let detail;
  try {
    detail = await client.fetchLeagueDetail(league.leagueId);
  } catch (error) {
    report.leaguesFailed += 1;
    report.failures.push({
      leagueId: league.leagueId,
      league: league.name,
      reason: error.response?.data?.message || error.message,
    });
    logger.warn("top league detail failed", {
      event: "top_league_failed",
      leagueId: league.leagueId,
      reason: error.message,
    });
    return;
  }
  const seasonId =
    detail.currentseason?.id ||
    detail.currentSeason?.id ||
    detail.current_season_id ||
    detail.currentSeasonId ||
    null;
  const teams = await client.fetchTeamsForLeague(league.leagueId, seasonId);
  report.leaguesImported += 1;
  report.teamsSeen += teams.length;
  logger.info("top league teams resolved", {
    event: "top_league_teams_resolved",
    leagueId: league.leagueId,
    league: league.name,
    seasonId,
    teamCount: teams.length,
  });

  let teamIndex = 0;
  for (const team of teams) {
    teamIndex += 1;
    if (options.teamLimit > 0 && teamIndex > options.teamLimit) {
      break;
    }
    await repository.upsertTeam({
      teamId: team.id,
      name: team.name,
      leagueId: league.leagueId,
    });
    await repository.upsertDefaultTactics(team.id);
    await repository.upsertDefaultManager({
      team_id: team.id,
      name: team.name,
    });

    let players;
    try {
      players = await client.fetchPlayersForTeam(team.id);
    } catch (error) {
      report.teamsFailed += 1;
      logger.warn("top league team players failed", {
        event: "top_league_team_failed",
        leagueId: league.leagueId,
        teamId: team.id,
        reason: error.response?.data?.message || error.message,
      });
      continue;
    }

    report.teamsImported += 1;
    report.playersSeen += players.length;
    let playerIndex = 0;
    for (const player of players) {
      playerIndex += 1;
      if (options.playerLimitPerTeam > 0 && playerIndex > options.playerLimitPerTeam) {
        break;
      }
      if (options.requireSportmonksImage && !player.sportmonksImageUrl) {
        report.playersSkippedNoImage += 1;
        continue;
      }
      await importPlayer(
        player,
        {
          leagueId: league.leagueId,
          teamId: team.id,
        },
        report,
      );
    }
  }
  await repository.setSyncState(`sportmonks:top-europe:${league.leagueId}`);
}

async function main() {
  const options = {
    teamLimit: envInt("TOP_LEAGUE_TEAM_LIMIT", 0, 0),
    playerLimitPerTeam: envInt("TOP_LEAGUE_PLAYER_LIMIT_PER_TEAM", 0, 0),
    requireSportmonksImage: envBool("TOP_LEAGUE_REQUIRE_SPORTMONKS_IMAGE", true),
  };
  const report = {
    selectedLeagues: selectedLeagues().map((league) => ({
      id: league.leagueId,
      name: league.name,
      country: league.country,
    })),
    leaguesImported: 0,
    leaguesFailed: 0,
    teamsSeen: 0,
    teamsImported: 0,
    teamsFailed: 0,
    playersSeen: 0,
    playersImported: 0,
    playersSkippedNoImage: 0,
    imagesUploaded: 0,
    imagesReused: 0,
    imageFailures: 0,
    failures: [],
  };
  const client = new SportmonksClient();
  for (const league of selectedLeagues()) {
    await importLeague(client, league, options, report);
  }
  await repository.setSyncState("sportmonks:top-europe");
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

main()
  .catch((error) => {
    process.stderr.write(
      `${JSON.stringify({
        event: "top_european_league_import_failed",
        reason: error.message,
      })}\n`,
    );
    process.exitCode = 1;
  })
  .finally(async () => {
    await db.close();
  });
