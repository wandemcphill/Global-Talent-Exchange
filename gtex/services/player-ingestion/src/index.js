"use strict";

const db = require("./db");
const { closeHealthServer, startHealthServer } = require("./health");
const { startWorkers } = require("./jobs");
const logger = require("./logger");
const { closeObservability, initObservability } = require("./observability");
const { closeQueues } = require("./queues");
const { runIngestionCycle } = require("./ingestionRun");
const { startScheduler } = require("./scheduler");

async function main() {
  const mode = process.argv[2] || "all";
  initObservability();
  await db.migrate();
  const healthServer = startHealthServer();

  if (mode === "once") {
    await runIngestionCycle({ trigger: "once", waitForIdle: false });
    await closeQueues();
    await closeHealthServer(healthServer);
    await db.close();
    await closeObservability();
    return;
  }

  const workers = mode === "worker" || mode === "all" ? startWorkers() : [];
  const scheduler = mode === "scheduler" || mode === "all" ? startScheduler() : null;
  if (workers.length === 0 && scheduler === null) {
    throw new Error(`Unknown ingestion mode: ${mode}`);
  }

  process.on("SIGTERM", () => {
    shutdown(workers, scheduler, healthServer).catch((error) => {
      logger.error("shutdown failed", { reason: error.message });
      process.exitCode = 1;
    });
  });
  process.on("SIGINT", () => {
    shutdown(workers, scheduler, healthServer).catch((error) => {
      logger.error("shutdown failed", { reason: error.message });
      process.exitCode = 1;
    });
  });
}

async function shutdown(workers, scheduler, healthServer) {
  logger.info("ingestion shutdown requested");
  if (scheduler) {
    scheduler.stop();
  }
  await closeHealthServer(healthServer);
  await closeQueues(workers);
  await db.close();
  await closeObservability();
}

if (require.main === module) {
  main().catch(async (error) => {
    const { captureException } = require("./observability");
    captureException(error, { extra: { phase: "service_start" } });
    logger.error("ingestion service failed", { reason: error.message });
    await db.close().catch(() => {});
    await closeObservability().catch(() => {});
    process.exitCode = 1;
  });
}

module.exports = { main };
