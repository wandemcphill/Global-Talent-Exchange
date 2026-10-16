"use strict";

const db = require("./db");
const logger = require("./logger");

async function main() {
  await db.migrate();
  logger.info("migrations complete");
  await db.close();
}

if (require.main === module) {
  main().catch(async (error) => {
    logger.error("migration failed", { reason: error.message });
    await db.close().catch(() => {});
    process.exitCode = 1;
  });
}

module.exports = { main };
