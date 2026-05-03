"use strict";

function relationshipKey(playerA, playerB) {
  const left = idValue(playerA);
  const right = idValue(playerB);
  return BigInt(left) < BigInt(right) ? [left, right] : [right, left];
}

function chemistryBonus(playerA, playerB, chemistry = 0) {
  return 1 + clamp(Number(chemistry) || 0, -1, 1) * 0.1;
}

function initialChemistry(playerA, playerB) {
  let chemistry = 0;
  if (playerA.nationality && playerA.nationality === playerB.nationality) {
    chemistry += 0.18;
  }
  if (playerA.position && playerA.position === playerB.position) {
    chemistry += 0.04;
  }
  if (Math.abs(Number(playerA.age || 24) - Number(playerB.age || 24)) <= 2) {
    chemistry += 0.05;
  }
  return clamp(chemistry, -1, 1);
}

function lineupChemistry(players, relationships = []) {
  if (players.length < 2) {
    return 0;
  }
  const relationshipMap = new Map(
    relationships.map((item) => [
      relationshipKey(item.player_a, item.player_b).join(":"),
      Number(item.chemistry || 0),
    ]),
  );
  let total = 0;
  let count = 0;
  for (let i = 0; i < players.length; i += 1) {
    for (let j = i + 1; j < players.length; j += 1) {
      const key = relationshipKey(players[i], players[j]).join(":");
      total += relationshipMap.get(key) ?? initialChemistry(players[i], players[j]);
      count += 1;
    }
  }
  return count === 0 ? 0 : clamp(total / count, -1, 1);
}

function evolveChemistry(current, outcome) {
  const delta = outcome.won ? 0.03 : outcome.lost ? -0.015 : 0.005;
  return clamp(Number(current || 0) + delta, -1, 1);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function idValue(player) {
  const value =
    typeof player === "object" && player !== null
      ? player.player_id || player.playerId || player.id
      : player;
  return String(value || "0");
}

module.exports = {
  chemistryBonus,
  evolveChemistry,
  initialChemistry,
  lineupChemistry,
  relationshipKey,
};
