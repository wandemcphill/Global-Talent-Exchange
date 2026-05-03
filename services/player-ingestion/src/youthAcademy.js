"use strict";

const config = require("./config");

function academyIdentity(team) {
  const name = String(team.name || team.team_name || "club").toLowerCase();
  if (name.includes("city") || name.includes("united")) {
    return "technical";
  }
  if (name.includes("athletic") || name.includes("sporting")) {
    return "physical";
  }
  return "balanced";
}

async function generateYouthForTeam(team, { count = null, reason = "youth_academy_intake" } = {}) {
  const { regenQueue } = require("./queues");
  const intake = count ?? config.season.regenPerSeason;
  let queued = 0;
  for (let index = 0; index < intake; index += 1) {
    await regenQueue.add(
      "generate-regen",
      {
        leagueId: team.league_id || team.leagueId || null,
        teamId: team.team_id || team.teamId,
        nationality: team.nationality_bias || null,
        reason,
        academyIdentity: academyIdentity(team),
      },
      { jobId: `academy:${team.team_id || team.teamId}:${Date.now()}:${index}` },
    );
    queued += 1;
  }
  return queued;
}

module.exports = {
  academyIdentity,
  generateYouthForTeam,
};
