"use strict";

const nodeCrypto = require("node:crypto");
const { faker } = require("@faker-js/faker");
const { generateRegenAttributes } = require("./footballAttributes");
const { stableHash } = require("./hash");

const COUNTRIES = [
  "Argentina",
  "Brazil",
  "England",
  "France",
  "Germany",
  "Ghana",
  "Italy",
  "Japan",
  "Netherlands",
  "Nigeria",
  "Portugal",
  "Senegal",
  "Spain",
  "United States",
];

function generateRegen({ leagueId = null, teamId = null, nationality = null } = {}) {
  const playerId = BigInt(Date.now()) * 10000n + BigInt(nodeCrypto.randomInt(10000));
  const seed = Number(playerId % 2147483647n);
  const country = nationality || COUNTRIES[nodeCrypto.randomInt(COUNTRIES.length)];
  const age = nodeCrypto.randomInt(16, 20);
  const attributes = generateRegenAttributes(seed, age);
  const player = {
    playerId: playerId.toString(),
    name: faker.person.fullName(),
    nationality: country,
    age,
    sportmonksImageUrl: null,
    isRegen: true,
    sourceProvider: "gtex_regen",
    leagueId,
    teamId,
    form: 0.5,
    sharpness: 0.5,
    isInjured: false,
    injuryReturnDate: null,
    minutesPlayed: 0,
    lastMatchRating: 0,
    ...attributes,
  };
  player.sourceHash = stableHash({
    playerId: player.playerId,
    name: player.name,
    nationality: player.nationality,
    age: player.age,
    leagueId,
    teamId,
    isRegen: true,
    position: player.position,
    overall: player.overall,
    potential: player.potential,
    traits: player.traits,
    personality: player.personality,
  });
  return player;
}

module.exports = {
  generateRegen,
};
