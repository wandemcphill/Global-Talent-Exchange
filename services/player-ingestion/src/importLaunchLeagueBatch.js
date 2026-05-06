"use strict";

const db = require("./db");
const { stableHash } = require("./hash");
const { uploadRemoteImage } = require("./images");
const logger = require("./logger");
const repository = require("./repository");
const { SportmonksClient } = require("./sportmonks");

const LAUNCH_EXPANSION_LEAGUES = [
  { code: "liga-mx", leagueId: 743, name: "Liga MX", country: "Mexico" },
  { code: "brasileirao-serie-a", leagueId: 648, name: "Serie A", country: "Brazil" },
  {
    code: "argentina-liga-profesional",
    leagueId: 636,
    name: "Liga Profesional de Futbol",
    country: "Argentina",
  },
  {
    code: "major-league-soccer",
    leagueId: 779,
    name: "Major League Soccer",
    country: "United States",
  },
  { code: "saudi-pro-league", leagueId: 944, name: "Pro League", country: "Saudi Arabia" },
  { code: "english-championship", leagueId: 9, name: "Championship", country: "England" },
  { code: "turkish-super-lig", leagueId: 600, name: "Super Lig", country: "Turkiye" },
  { code: "scottish-premiership", leagueId: 501, name: "Premiership", country: "Scotland" },
  { code: "npfl", leagueId: 1475, name: "Npfl", country: "Nigeria" },
  {
    code: "south-africa-premier-league",
    leagueId: 806,
    name: "Premier League",
    country: "South Africa",
  },
  { code: "la-liga-2", leagueId: 567, name: "La Liga 2", country: "Spain" },
  { code: "ligue-2", leagueId: 304, name: "Ligue 2", country: "France" },
  { code: "serie-b", leagueId: 387, name: "Serie B", country: "Italy" },
  { code: "2-bundesliga", leagueId: 85, name: "2. Bundesliga", country: "Germany" },
  { code: "swiss-super-league", leagueId: 591, name: "Super League", country: "Switzerland" },
  { code: "belgian-pro-league", leagueId: 208, name: "Pro League", country: "Belgium" },
  { code: "austrian-bundesliga", leagueId: 181, name: "Admiral Bundesliga", country: "Austria" },
  { code: "russian-premier-league", leagueId: 486, name: "Premier League", country: "Russia" },
  { code: "ukrainian-premier-league", leagueId: 609, name: "Premier League", country: "Ukraine" },
  { code: "swedish-allsvenskan", leagueId: 573, name: "Allsvenskan", country: "Sweden" },
  { code: "norwegian-eliteserien", leagueId: 444, name: "Eliteserien", country: "Norway" },
  { code: "czech-chance-liga", leagueId: 262, name: "Chance Liga", country: "Czech Republic" },
  { code: "polish-ekstraklasa", leagueId: 453, name: "Ekstraklasa", country: "Poland" },
  { code: "egyptian-premier-league", leagueId: 830, name: "Premier League", country: "Egypt" },
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
  const requested = (process.env.LAUNCH_LEAGUE_IDS || "")
    .split(",")
    .map((item) => Number.parseInt(item.trim(), 10))
    .filter((item) => Number.isFinite(item) && item > 0);
  if (!requested.length) {
    return LAUNCH_EXPANSION_LEAGUES;
  }
  const requestedSet = new Set(requested);
  return LAUNCH_EXPANSION_LEAGUES.filter((league) => requestedSet.has(league.leagueId));
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

async function storeSportmonksPortrait(player, existing) {
  if (existing?.source_url && existing?.storage_key && isReusableImageUrl(existing.source_url)) {
    return {
      imageUrl: existing.source_url,
      storageKey: existing.storage_key,
      imageSource: "sportmonks",
      rightsCleared: true,
      reused: true,
    };
  }
  if (!player.sportmonksImageUrl) {
    return {
      imageUrl: null,
      storageKey: null,
      imageSource: "missing",
      rightsCleared: false,
      reused: false,
    };
  }
  const uploaded = await uploadRemoteImage(
    player.sportmonksImageUrl,
    player.playerId,
    "sportmonks",
  );
  return {
    imageUrl: uploaded.secure_url,
    storageKey: uploaded.public_id,
    imageSource: "sportmonks",
    rightsCleared: true,
    reused: false,
  };
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
    logger.warn("launch league portrait upload failed", {
      event: "launch_league_portrait_failed",
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
  logger.info("launch league player imported", {
    event: "launch_league_player_imported",
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
  logger.info("launch league teams resolved", {
    event: "launch_league_teams_resolved",
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
      logger.warn("launch league team players failed", {
        event: "launch_league_team_failed",
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
  await repository.setSyncState(`sportmonks:launch-league:${league.leagueId}`);
}

async function main() {
  const options = {
    teamLimit: envInt("LAUNCH_LEAGUE_TEAM_LIMIT", 0, 0),
    playerLimitPerTeam: envInt("LAUNCH_LEAGUE_PLAYER_LIMIT_PER_TEAM", 0, 0),
    requireSportmonksImage: envBool("LAUNCH_LEAGUE_REQUIRE_SPORTMONKS_IMAGE", true),
  };
  const leagues = selectedLeagues();
  const report = {
    selectedLeagues: leagues.map((league) => ({
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
  for (const league of leagues) {
    await importLeague(client, league, options, report);
  }
  await repository.setSyncState("sportmonks:launch-league-batch");
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

main()
  .catch((error) => {
    process.stderr.write(
      `${JSON.stringify({
        event: "launch_league_batch_import_failed",
        reason: error.message,
      })}\n`,
    );
    process.exitCode = 1;
  })
  .finally(async () => {
    await db.close();
  });
