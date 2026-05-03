"use strict";

const {
  buildMatchPlayer,
  effectiveStat,
  postMatchUpdate,
  staminaDrain,
} = require("./matchInfluence");

function applyTactics(team, player) {
  let modifier = 1;
  const style = String(team.style || "balanced").toLowerCase();
  if (style === "possession") {
    modifier += (player.passing || 50) * 0.002;
  }
  if (style === "counter") {
    modifier += (player.pace || 50) * 0.003;
  }
  if ((team.pressing || 0) > 70) {
    player.fitness = Math.max(0, (player.fitness || 100) - 0.02);
  }
  return modifier;
}

function formationBonus(position, formation) {
  const normalizedPosition = String(position || "").toUpperCase();
  if (formation === "4-3-3" && normalizedPosition === "FW") {
    return 1.1;
  }
  if (formation === "5-3-2" && normalizedPosition === "DF") {
    return 1.1;
  }
  return 1;
}

function tacticalClash(teamA, teamB) {
  return (
    (teamA.tempo || 50) + (teamA.pressing || 50) > (teamB.line_height || 50) + (teamB.width || 50)
  );
}

function applyTraits(player, event) {
  const traits = new Set(player.traits || []);
  const next = { ...event };
  if (traits.has("long_shots")) {
    next.shotChance = (next.shotChance || 0) + 10;
  }
  if (traits.has("playmaker")) {
    next.passAccuracy = (next.passAccuracy || 0) + 10;
  }
  if (traits.has("press_resistant")) {
    next.turnoverRisk = Math.max(0, (next.turnoverRisk || 0) - 8);
  }
  return next;
}

function personalityImpact(player) {
  const next = { ...player };
  if (next.personality === "ambitious") {
    next.potential = Math.min(99, (next.potential || 0) + 2);
  }
  if (next.personality === "lazy") {
    next.fitness = Math.max(0, (next.fitness || 100) - 0.1);
  }
  if (next.personality === "professional") {
    next.fitness = Math.min(100, (next.fitness || 100) + 0.05);
  }
  return next;
}

function duel(attacker, defender) {
  return (
    (attacker.pace || 0) + (attacker.dribbling || 0) + ((attacker.morale || 50) / 100) * 20 >
    (defender.defending || 0) + (defender.physical || 0)
  );
}

function shot(player, random = Math.random) {
  return random() * 100 < (player.shooting || 0);
}

function progression(player, rating) {
  const next = { ...player };
  if ((next.age || 24) < 23) {
    next.overall = Math.min(next.potential || 99, (next.overall || 45) + rating * 0.05);
  }
  next.morale = Math.min(100, (next.morale || 50) + 0.03);
  return personalityImpact(next);
}

function evaluateTransfer(player, team) {
  return (player.overall || 0) > (team.avgOverall || 50) + 5;
}

function scoutPlayers(_team, pool) {
  return pool.filter((player) => (player.potential || 0) > 80 && (player.age || 99) < 21);
}

function simulateMatchSnapshot(home, away, random = Math.random) {
  const homePlayers = normalizeMatchPlayers(home.players || []);
  const awayPlayers = normalizeMatchPlayers(away.players || []);
  const homeClash = tacticalClash(home.tactics || {}, away.tactics || {});
  const homePossession = homeClash ? 54 : 48;
  const awayPossession = 100 - homePossession;
  const homeChanceRate = chanceRate(
    { ...home, players: homePlayers },
    { ...away, players: awayPlayers },
    homeClash,
  );
  const awayChanceRate = chanceRate(
    { ...away, players: awayPlayers },
    { ...home, players: homePlayers },
    !homeClash,
  );
  return {
    homeGoals: resolveGoals(homePlayers, homeChanceRate, random),
    awayGoals: resolveGoals(awayPlayers, awayChanceRate, random),
    possession: {
      home: homePossession,
      away: awayPossession,
    },
  };
}

function chanceRate(team, opponent, hasTacticalEdge) {
  const attack = average(team.players || [], ["pace", "shooting", "passing", "dribbling"]);
  const defense = average(opponent.players || [], ["defending", "physical"]);
  return Math.max(4, Math.min(18, 8 + (attack - defense) / 8 + (hasTacticalEdge ? 2 : -1)));
}

function resolveGoals(players, chanceRate, random) {
  const attackers = players.filter((player) => ["FW", "MF"].includes(player.position));
  let goals = 0;
  for (let chance = 0; chance < chanceRate; chance += 1) {
    const shooter = attackers[Math.floor(random() * Math.max(attackers.length, 1))] || players[0];
    if (shooter && shot(shooter, random)) {
      goals += 1;
    }
  }
  return goals;
}

function normalizeMatchPlayers(players) {
  return players
    .map((player) => {
      const snapshot = player.stats ? player : buildMatchPlayer(player);
      return {
        ...player,
        ...snapshot.stats,
        position: snapshot.position || player.position,
        state: snapshot.state,
        available: snapshot.available,
      };
    })
    .filter((player) => player.available !== false);
}

function average(players, keys) {
  if (!players.length) {
    return 50;
  }
  const total = players.reduce(
    (sum, player) =>
      sum + keys.reduce((inner, key) => inner + Number(player[key] || 50), 0) / keys.length,
    0,
  );
  return total / players.length;
}

module.exports = {
  applyTactics,
  applyTraits,
  buildMatchPlayer,
  duel,
  evaluateTransfer,
  effectiveStat,
  formationBonus,
  personalityImpact,
  postMatchUpdate,
  progression,
  scoutPlayers,
  shot,
  simulateMatchSnapshot,
  staminaDrain,
  tacticalClash,
};
