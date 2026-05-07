"use strict";

const assert = require("node:assert/strict");

const { safeJobId } = require("./jobIds");

assert.equal(safeJobId("league", "123", "run:2026:05:07"), "league-123-run_2026_05_07");
assert.equal(
  safeJobId("player", "sportmonks:42", "hash/value?x=1"),
  "player-sportmonks_42-hash_value_x_1",
);
assert.equal(safeJobId("regen", null, undefined, 7), "regen-none-none-7");
