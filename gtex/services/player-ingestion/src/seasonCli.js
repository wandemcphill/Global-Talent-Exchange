"use strict";

const db = require("./db");
const logger = require("./logger");
const { closeQueues } = require("./queues");
const {
  createCompetitionSchedule,
  createSeasonSchedule,
  endSeason,
  getStandings,
  runMatchday,
} = require("./seasonEngine");
const { createScoutingAssignment, runScoutingAssignment } = require("./scoutingService");

async function main() {
  await db.migrate();
  const [command, ...args] = process.argv.slice(2);
  const flags = parseFlags(args);

  if (command === "create") {
    const teamIds = flags.teams
      ? flags.teams.split(",").map((value) => Number(value.trim()))
      : null;
    const result = await createSeasonSchedule({
      name: flags.name,
      startDate: flags.start || new Date(),
      endDate: flags.end || null,
      leagueId: flags.leagueId ? Number(flags.leagueId) : null,
      teamIds,
      fixturesPerDay: flags.fixturesPerDay ? Number(flags.fixturesPerDay) : undefined,
    });
    logger.info("season create command complete", {
      event: "season_cli_create_complete",
      seasonId: result.season.id,
      fixtureCount: result.fixtureCount,
      teamCount: result.teamCount,
    });
    return;
  }

  if (command === "competition:create") {
    const seasonId = Number(flags.seasonId || flags.season);
    if (!seasonId) {
      throw new Error("--season-id is required");
    }
    const teamIds = flags.teams ? flags.teams.split(",").map((value) => Number(value.trim())) : [];
    const result = await createCompetitionSchedule({
      seasonId,
      name: flags.name || "GTEX Cup",
      type: flags.type || "cup",
      teamIds,
      startDate: flags.start || new Date(),
    });
    logger.info("competition create command complete", {
      event: "season_cli_competition_create_complete",
      competitionId: result.competition.id,
      fixtureCount: result.fixtureCount,
      teamCount: result.teamCount,
    });
    return;
  }

  if (command === "tick") {
    const result = await runMatchday(flags.date || new Date());
    logger.info("season tick command complete", {
      event: "season_cli_tick_complete",
      fixtureCount: result.fixtureCount,
      transferCount: result.transferCount,
    });
    return;
  }

  if (command === "standings") {
    const seasonId = Number(flags.seasonId || flags.season);
    if (!seasonId) {
      throw new Error("--season-id is required");
    }
    const rows = await getStandings(seasonId);
    process.stdout.write(`${JSON.stringify(rows, null, 2)}\n`);
    return;
  }

  if (command === "end") {
    const seasonId = Number(flags.seasonId || flags.season);
    if (!seasonId) {
      throw new Error("--season-id is required");
    }
    const result = await endSeason(seasonId);
    logger.info("season end command complete", {
      event: "season_cli_end_complete",
      seasonId,
      queuedRegens: result.queuedRegens,
    });
    return;
  }

  if (command === "scout:create") {
    const teamId = Number(flags.teamId || flags.team);
    if (!teamId || !flags.region) {
      throw new Error("--team-id and --region are required");
    }
    const assignment = await createScoutingAssignment({
      teamId,
      region: flags.region,
      minPotential: flags.minPotential ? Number(flags.minPotential) : 75,
    });
    logger.info("scouting assignment created", {
      event: "season_cli_scout_create_complete",
      assignmentId: assignment.id,
      teamId,
      region: assignment.region,
    });
    return;
  }

  if (command === "scout:run") {
    const assignmentId = Number(flags.assignmentId || flags.assignment);
    if (!assignmentId) {
      throw new Error("--assignment-id is required");
    }
    const reports = await runScoutingAssignment(assignmentId);
    logger.info("scouting assignment run complete", {
      event: "season_cli_scout_run_complete",
      assignmentId,
      reportCount: reports.length,
    });
    return;
  }

  throw new Error(
    "Usage: node src/seasonCli.js create|competition:create|tick|standings|end|scout:create|scout:run [--name ...] [--type league|cup|continental] [--league-id ...] [--teams 1,2] [--start YYYY-MM-DD] [--date YYYY-MM-DD] [--season-id 1]",
  );
}

function parseFlags(args) {
  const flags = {};
  for (let index = 0; index < args.length; index += 1) {
    const item = args[index];
    if (!item.startsWith("--")) {
      continue;
    }
    const key = camelCase(item.slice(2));
    const next = args[index + 1];
    if (!next || next.startsWith("--")) {
      flags[key] = "true";
      continue;
    }
    flags[key] = next;
    index += 1;
  }
  return flags;
}

function camelCase(value) {
  return value.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
}

if (require.main === module) {
  main()
    .catch((error) => {
      logger.error("season command failed", {
        event: "season_cli_failed",
        reason: error.message,
      });
      process.exitCode = 1;
    })
    .finally(async () => {
      await closeQueues().catch(() => {});
      await db.close().catch(() => {});
    });
}
