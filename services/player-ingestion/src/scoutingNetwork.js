"use strict";

function scoutRegion(region, players, { minPotential = 75 } = {}) {
  const normalizedRegion = String(region || "")
    .trim()
    .toLowerCase();
  return players
    .filter(
      (player) =>
        String(player.nationality || "")
          .trim()
          .toLowerCase() === normalizedRegion,
    )
    .filter((player) => Number(player.potential || 0) >= minPotential)
    .sort((a, b) => fitScore(b) - fitScore(a));
}

function fitScore(player) {
  const potential = Number(player.potential || 50);
  const age = Number(player.age || 24);
  const form = Number(player.form ?? 0.5);
  const upside = Math.max(0, 24 - age) * 1.5;
  return potential + upside + form * 10;
}

function scoutingSummary(player) {
  return `${player.name || "Player"} profiles as a ${player.position || "prospect"} with ${player.potential || 0} potential.`;
}

module.exports = {
  fitScore,
  scoutRegion,
  scoutingSummary,
};
