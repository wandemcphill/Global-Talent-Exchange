"use strict";

const nodeCrypto = require("node:crypto");

function stableHash(payload) {
  return nodeCrypto.createHash("sha256").update(JSON.stringify(payload)).digest("hex");
}

module.exports = { stableHash };
