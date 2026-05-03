"use strict";

const MENTALITIES = ["attacking", "defensive", "balanced"];

function defaultManagerForTeam(team) {
  const teamId = Number(team.team_id || team.teamId || team);
  const seed = numericSeed(teamId);
  return {
    teamId,
    name: `${team.name || "Club"} Manager`,
    mentality: MENTALITIES[seed % MENTALITIES.length],
    adaptability: 45 + (seed % 41),
    risk: 35 + (Math.floor(seed / 7) % 51),
  };
}

function pickLineup(players, manager, size = 11) {
  const available = players
    .filter((player) => !player.is_injured && !player.isInjured && !player.is_retired)
    .sort((a, b) => playerSelectionScore(b, manager) - playerSelectionScore(a, manager));
  return {
    starters: available.slice(0, size),
    bench: available.slice(size, size + 7),
  };
}

function chooseTactics(manager, opponentStrength) {
  const mentality = String(manager?.mentality || "balanced").toLowerCase();
  const risk = Number(manager?.risk || 50);
  const strength = Number(opponentStrength || 50);

  if (mentality === "attacking" && strength < 60) {
    return "high_press";
  }
  if (strength > 70 && risk < 75) {
    return "defensive_block";
  }
  if (mentality === "defensive" && strength >= 55) {
    return "compact_counter";
  }
  if (risk > 75 && strength < 68) {
    return "front_foot";
  }
  return "balanced";
}

function tacticProfile(decision) {
  return {
    high_press: {
      style: "possession",
      pressing: 78,
      tempo: 66,
      width: 64,
      line_height: 72,
    },
    defensive_block: {
      style: "balanced",
      pressing: 42,
      tempo: 44,
      width: 48,
      line_height: 35,
    },
    compact_counter: {
      style: "counter",
      pressing: 54,
      tempo: 72,
      width: 52,
      line_height: 44,
    },
    front_foot: {
      style: "direct",
      pressing: 70,
      tempo: 76,
      width: 68,
      line_height: 66,
    },
    all_out_attack: {
      style: "direct",
      pressing: 82,
      tempo: 84,
      width: 74,
      line_height: 78,
    },
    park_the_bus: {
      style: "balanced",
      pressing: 36,
      tempo: 34,
      width: 42,
      line_height: 30,
    },
    balanced: {
      style: "balanced",
      pressing: 56,
      tempo: 56,
      width: 56,
      line_height: 56,
    },
  }[decision || "balanced"];
}

function adjustTactics(scoreDelta, minute, manager) {
  const adaptability = Number(manager?.adaptability || 50);
  if (scoreDelta < 0 && minute > 60 && adaptability >= 35) {
    return "all_out_attack";
  }
  if (scoreDelta > 0 && minute > 75 && adaptability >= 30) {
    return "park_the_bus";
  }
  return null;
}

function makeSubstitution(team) {
  const tired = (team.players || [])
    .filter((player) => Number(player.fitness ?? 100) < 30)
    .sort((a, b) => Number(a.fitness ?? 100) - Number(b.fitness ?? 100))[0];
  const bench = [...(team.bench || [])].sort(
    (a, b) => Number(b.overall || 50) - Number(a.overall || 50),
  );
  if (tired && bench.length) {
    return {
      out: tired,
      in: bench[0],
    };
  }
  return null;
}

function managerPressureDelta({ won, lost, upsetWin, upsetLoss }) {
  if (upsetWin) {
    return -0.12;
  }
  if (upsetLoss) {
    return 0.18;
  }
  if (won) {
    return -0.05;
  }
  if (lost) {
    return 0.08;
  }
  return 0.01;
}

function playerSelectionScore(player, manager = {}) {
  const base = Number(player.overall || 50) * Number(player.form ?? 0.5);
  const fitness = Number(player.fitness ?? 100) / 100;
  const mentality = String(manager.mentality || "balanced").toLowerCase();
  const attackingBias = mentality === "attacking" && ["FW", "MF"].includes(player.position) ? 4 : 0;
  const defensiveBias = mentality === "defensive" && ["GK", "DF"].includes(player.position) ? 4 : 0;
  return base + fitness * 10 + attackingBias + defensiveBias;
}

function numericSeed(value) {
  const text = String(value || "0");
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = (hash * 31 + text.charCodeAt(index)) % 100000;
  }
  return hash;
}

module.exports = {
  adjustTactics,
  chooseTactics,
  defaultManagerForTeam,
  makeSubstitution,
  managerPressureDelta,
  pickLineup,
  tacticProfile,
};
