"use strict";

const { stableHash } = require("./hash");

const TRAITS = [
  "long_shots",
  "playmaker",
  "press_resistant",
  "ball_winner",
  "aerial_threat",
  "leader",
  "set_piece_specialist",
  "big_match",
  "high_work_rate",
  "counter_runner",
];

const PERSONALITIES = [
  "ambitious",
  "professional",
  "loyal",
  "temperamental",
  "resilient",
  "lazy",
  "leader",
  "balanced",
];

// Weighted fallback pool for when a real position is unavailable: roughly a
// real squad shape (~10% GK, ~30% each outfield) instead of a flat 25% per
// bucket, which over-produced goalkeepers.
const FALLBACK_POSITION_POOL = [
  "GK",
  "DF",
  "DF",
  "DF",
  "MF",
  "MF",
  "MF",
  "FW",
  "FW",
  "FW",
];

const POSITION_GROUPS = {
  goalkeeper: "GK",
  keeper: "GK",
  defender: "DF",
  centreback: "DF",
  centerback: "DF",
  back: "DF",
  wingback: "DF",
  midfielder: "MF",
  defensive: "MF",
  attackingmidfielder: "MF",
  winger: "FW",
  forward: "FW",
  striker: "FW",
  attacker: "FW",
};

function deriveAttributes(player) {
  const seed = numericSeed(player.playerId || player.name || Date.now());
  const position = normalizePosition(player.position) || pickBySeed(FALLBACK_POSITION_POOL, seed);
  const age = clampInt(player.age || 24, 15, 45);
  const youngUpside = age <= 21 ? 8 : age >= 31 ? -4 : 2;
  const base = clampInt(52 + (seed % 31) + (player.isRegen ? -2 : 0), 45, 88);
  const potential = clampInt(
    base + youngUpside + (shifted(seed, 3) % 18),
    base,
    player.isRegen ? 95 : 92,
  );
  const archetype = positionArchetype(position, seed);
  const traits =
    player.traits && player.traits.length ? player.traits : generateTraits(seed, position);
  const personality = player.personality || PERSONALITIES[shifted(seed, 11) % PERSONALITIES.length];
  return {
    position,
    overall: clampInt(player.overall || base, 1, 99),
    potential,
    pace: clampInt(player.pace || archetype.pace, 1, 99),
    shooting: clampInt(player.shooting || archetype.shooting, 1, 99),
    passing: clampInt(player.passing || archetype.passing, 1, 99),
    dribbling: clampInt(player.dribbling || archetype.dribbling, 1, 99),
    defending: clampInt(player.defending || archetype.defending, 1, 99),
    physical: clampInt(player.physical || archetype.physical, 1, 99),
    morale: clampFloat(player.morale ?? 50.0, 0, 100),
    fitness: clampFloat(player.fitness ?? 100.0, 0, 100),
    traits,
    personality,
  };
}

function generateRegenAttributes(seed, age) {
  const position = pickBySeed(FALLBACK_POSITION_POOL, seed);
  const overall = clampInt(45 + (seed % 26), 45, 70);
  const potential = clampInt(Math.max(70 + (shifted(seed, 5) % 26), overall + 8), 70, 95);
  return {
    ...deriveAttributes({
      playerId: seed,
      age,
      isRegen: true,
      position,
      overall,
      potential,
    }),
    position,
    overall,
    potential,
  };
}

function generateTraits(seed, position) {
  const pool = [...TRAITS];
  if (position === "FW") {
    pool.push("long_shots", "counter_runner");
  } else if (position === "MF") {
    pool.push("playmaker", "press_resistant");
  } else if (position === "DF") {
    pool.push("ball_winner", "leader");
  } else if (position === "GK") {
    pool.push("leader", "big_match");
  }
  return Array.from(
    new Set([pool[seed % pool.length], pool[shifted(seed, 7) % pool.length]]),
  ).slice(0, 2);
}

function normalizePosition(value) {
  const raw = String(value || "")
    .toLowerCase()
    .replace(/[^a-z]/g, "");
  if (!raw) {
    return null;
  }
  if (["gk", "df", "mf", "fw"].includes(raw)) {
    return raw.toUpperCase();
  }
  for (const [token, group] of Object.entries(POSITION_GROUPS)) {
    if (raw.includes(token)) {
      return group;
    }
  }
  return null;
}

function positionArchetype(position, seed) {
  const jitter = (offset) => (shifted(seed, offset) % 15) - 7;
  const base = {
    GK: { pace: 44, shooting: 18, passing: 58, dribbling: 32, defending: 78, physical: 72 },
    DF: { pace: 62, shooting: 34, passing: 58, dribbling: 50, defending: 75, physical: 76 },
    MF: { pace: 66, shooting: 58, passing: 75, dribbling: 72, defending: 60, physical: 68 },
    FW: { pace: 76, shooting: 75, passing: 62, dribbling: 74, defending: 35, physical: 68 },
  }[position];
  return {
    pace: base.pace + jitter(1),
    shooting: base.shooting + jitter(3),
    passing: base.passing + jitter(5),
    dribbling: base.dribbling + jitter(7),
    defending: base.defending + jitter(9),
    physical: base.physical + jitter(11),
  };
}

function numericSeed(value) {
  const hash = stableHash({ value });
  return Number.parseInt(hash.slice(0, 10), 16);
}

function pickBySeed(items, seed) {
  return items[seed % items.length];
}

function shifted(seed, offset) {
  return Math.floor(seed / 2 ** offset);
}

function clampInt(value, min, max) {
  return Math.max(min, Math.min(max, Math.round(Number(value) || min)));
}

function clampFloat(value, min, max) {
  return Math.max(min, Math.min(max, Number(value) || min));
}

module.exports = {
  deriveAttributes,
  generateRegenAttributes,
  normalizePosition,
};
