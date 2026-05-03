"use strict";

const config = require("./config");
const { stableHash } = require("./hash");
const { resolveAndStoreImage } = require("./images");
const logger = require("./logger");
const { applyPlayerInfluence } = require("./matchInfluence");
const { captureException } = require("./observability");
const { createWorker, leagueQueue, playerQueue, regenQueue, teamQueue } = require("./queues");
const repository = require("./repository");
const { generateRegen } = require("./regen");
const { processSeasonJob } = require("./seasonJobs");
const { SportmonksClient } = require("./sportmonks");

const sportmonks = new SportmonksClient();

async function enqueueLeagues({ runId = Date.now() } = {}) {
  const leagues = await sportmonks.fetchLeagues();
  for (const league of leagues) {
    const leagueId = Number(league.id);
    if (!leagueId) {
      continue;
    }
    await leagueQueue.add(
      "sync-league",
      {
        leagueId,
        seasonId: league.currentseason?.id || league.currentSeason?.id || null,
      },
      { jobId: `league:${leagueId}:${runId}` },
    );
  }
  logger.info("league jobs queued", {
    event: "league_jobs_queued",
    count: leagues.length,
    runId,
  });
  return { queuedLeagues: leagues.length, runId };
}

async function processLeague(job) {
  const { leagueId, seasonId } = job.data;
  const teams = await sportmonks.fetchTeamsForLeague(leagueId, seasonId);
  const lastLeagueSync =
    (await repository.getSyncState("players")) ||
    (await repository.getSyncState(`sportmonks:league:${leagueId}`));
  if (config.sportmonks.updatedSinceSupported && lastLeagueSync) {
    const updatedPlayers = await sportmonks.fetchUpdatedPlayersSince(lastLeagueSync);
    for (const player of updatedPlayers) {
      await enqueuePlayer(player, { leagueId });
    }
  }
  for (const team of teams) {
    await teamQueue.add(
      "sync-team",
      {
        leagueId,
        seasonId: team.seasonId || seasonId || null,
        teamId: team.id,
        teamName: team.name || null,
      },
      { jobId: `team:${leagueId}:${team.id}:${job.id}` },
    );
  }
  for (let index = 0; index < config.regen.youthPlayersPerLeague; index += 1) {
    await regenQueue.add(
      "generate-regen",
      { leagueId },
      { jobId: `regen:${leagueId}:${Date.now()}:${index}` },
    );
  }
  await repository.setSyncState(`sportmonks:league:${leagueId}`);
  logger.info("league processed", { event: "league_processed", leagueId, teamCount: teams.length });
}

async function processTeam(job) {
  const { leagueId, teamId, teamName } = job.data;
  await repository.upsertTeam({
    teamId,
    name: teamName || null,
    leagueId,
  });
  await repository.upsertDefaultTactics(teamId);
  await repository.upsertDefaultManager({
    team_id: teamId,
    name: teamName,
  });
  const players = await sportmonks.fetchPlayersForTeam(teamId);
  for (const player of players) {
    await enqueuePlayer(player, { leagueId, teamId });
  }
  await repository.setSyncState(`sportmonks:team:${teamId}`);
  logger.info("team processed", {
    event: "team_processed",
    leagueId,
    teamId,
    playerCount: players.length,
  });
}

async function enqueuePlayer(player, context = {}) {
  if (!player.playerId) {
    return;
  }
  const normalized = withSourceHash({
    ...player,
    leagueId: player.leagueId || context.leagueId || null,
    teamId: player.teamId || context.teamId || null,
  });
  await playerQueue.add("upsert-player", normalized, {
    jobId: `player:${normalized.playerId}:${normalized.sourceHash}`,
  });
}

async function processPlayer(job) {
  const player = withSourceHash(job.data);
  const existing = await repository.getPlayer(player.playerId);
  const influence = applyPlayerInfluence(existing, player);
  const matchStateChanged = hasMatchStateChanged(existing, influence);
  if (existing?.source_hash === player.sourceHash && existing?.image_url && !matchStateChanged) {
    logger.info("player unchanged", {
      event: "player_processed",
      playerId: player.playerId,
      status: "unchanged",
      hasImage: true,
      form: existing.form,
      sharpness: existing.sharpness,
      isInjured: existing.is_injured,
    });
    return { status: "unchanged" };
  }

  const image = await resolvePlayerImage(player, existing);
  if (!image.imageUrl && !player.isRegen) {
    await regenQueue.add("generate-regen", {
      basePlayerId: player.playerId,
      leagueId: player.leagueId,
      teamId: player.teamId,
      nationality: player.nationality,
      reason: "missing_player_image",
    });
    logger.info("regen queued for missing image", {
      event: "regen_queued",
      basePlayerId: player.playerId,
      leagueId: player.leagueId,
      teamId: player.teamId,
      reason: "missing_player_image",
    });
  }

  const changed = await repository.upsertPlayer({
    ...player,
    imageUrl: image.imageUrl,
    imageSource: image.imageSource,
    rightsCleared: image.rightsCleared,
    form: influence.form,
    sharpness: influence.sharpness,
    isInjured: influence.isInjured,
    injuryReturnDate: influence.injuryReturnDate,
    minutesPlayed: influence.minutesPlayed,
    lastMatchRating: influence.lastMatchRating,
    morale: influence.morale,
  });
  const appPlayerId = await repository.upsertAppPlayerMirror(player);
  const appImageChanged = await repository.upsertAppPlayerImageMetadata({
    appPlayerId,
    playerId: player.playerId,
    imageUrl: image.imageUrl,
    storageKey: image.storageKey,
    rightsCleared: image.rightsCleared,
  });
  if (influence.transferDetected) {
    await repository.recordTransfer({
      playerId: player.playerId,
      fromTeam: influence.previousTeamId,
      toTeam: player.teamId,
      source: "sportmonks",
    });
    logger.info("player transfer applied", {
      event: "player_transfer_applied",
      playerId: player.playerId,
      fromTeam: influence.previousTeamId,
      toTeam: player.teamId,
    });
  }
  await recalculateAffectedTeams(player.teamId, influence.previousTeamId);
  logger.info("player upsert complete", {
    event: "player_processed",
    playerId: player.playerId,
    changed,
    hasImage: Boolean(image.imageUrl),
    imageSource: image.imageSource,
    appImageChanged,
    form: influence.form,
    sharpness: influence.sharpness,
    isInjured: influence.isInjured,
    lastMatchRating: influence.lastMatchRating,
    minutesPlayed: influence.minutesPlayed,
  });
  return { status: changed ? "changed" : "noop" };
}

async function processRegen(job) {
  const player = generateRegen(job.data || {});
  const image = await resolveAndStoreImage(player, { allowAiFallback: true });
  const changed = await repository.upsertPlayer({
    ...player,
    imageUrl: image.imageUrl,
    imageSource: image.imageSource,
    rightsCleared: image.rightsCleared,
  });
  await recalculateAffectedTeams(player.teamId);
  logger.info("regen upsert complete", {
    event: "regen_processed",
    playerId: player.playerId,
    leagueId: player.leagueId,
    changed,
    hasImage: Boolean(image.imageUrl),
    imageSource: image.imageSource,
  });
  return { status: changed ? "created" : "noop" };
}

async function resolvePlayerImage(player, existing) {
  const existingSource = String(existing?.image_source || "");
  const shouldResolve =
    !existing?.image_url ||
    existingSource === "missing" ||
    existingSource.includes("remote_fallback") ||
    (player.sportmonksImageUrl && existingSource !== "sportmonks");

  if (shouldResolve) {
    return resolveAndStoreImage(player, { allowAiFallback: Boolean(player.isRegen) });
  }

  return {
    imageUrl: existing.image_url,
    storageKey: null,
    imageSource: existing.image_source,
    rightsCleared: existing.rights_cleared,
  };
}

function withSourceHash(player) {
  const sourceHash =
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
      form: player.form,
      sharpness: player.sharpness,
      isInjured: player.isInjured,
      injuryReturnDate: player.injuryReturnDate,
      minutesPlayed: player.minutesPlayed,
      lastMatchRating: player.lastMatchRating,
    });
  return {
    ...player,
    sourceHash,
  };
}

async function recalculateAffectedTeams(...teamIds) {
  const uniqueTeamIds = [...new Set(teamIds.filter(Boolean).map((teamId) => Number(teamId)))];
  for (const teamId of uniqueTeamIds) {
    const strength = await repository.recalculateTeamStrength(teamId);
    logger.info("team strength recalculated", {
      event: "team_strength_recalculated",
      teamId,
      strength,
    });
  }
}

function hasMatchStateChanged(existing, influence) {
  if (!existing) {
    return true;
  }
  return (
    Number(existing.form ?? 0.5) !== Number(influence.form) ||
    Number(existing.sharpness ?? 0.5) !== Number(influence.sharpness) ||
    Boolean(existing.is_injured) !== Boolean(influence.isInjured) ||
    String(existing.injury_return_date || "") !== String(influence.injuryReturnDate || "") ||
    Number(existing.minutes_played || 0) !== Number(influence.minutesPlayed) ||
    Number(existing.last_match_rating || 0) !== Number(influence.lastMatchRating)
  );
}

function startWorkers() {
  const workers = [
    createWorker(config.queues.league, processLeague),
    createWorker(config.queues.team, processTeam),
    createWorker(config.queues.player, processPlayer),
    createWorker(config.queues.regen, processRegen),
    createWorker(config.queues.season, processSeasonJob),
  ];
  for (const worker of workers) {
    worker.on("failed", (job, error) => {
      captureException(error, {
        tags: { queue: worker.name },
        extra: { jobId: job?.id, jobName: job?.name },
      });
      logger.error("job failed", {
        event: "queue_job_failed",
        queue: worker.name,
        jobId: job?.id,
        reason: error.message,
      });
    });
  }
  logger.info("ingestion workers started", { concurrency: config.queues.concurrency });
  return workers;
}

module.exports = {
  enqueueLeagues,
  startWorkers,
};
