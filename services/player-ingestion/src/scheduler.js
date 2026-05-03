"use strict";

const cron = require("node-cron");
const config = require("./config");
const { runIngestionCycle } = require("./ingestionRun");
const logger = require("./logger");
const { enqueueSeasonTick } = require("./seasonJobs");

function startScheduler() {
  const tasks = [];
  const ingestionTask = cron.schedule(config.scheduler.cron, async () => {
    try {
      await runIngestionCycle({ trigger: "cron" });
    } catch (error) {
      logger.error("scheduled ingestion failed", { reason: error.message });
    }
  });
  tasks.push(ingestionTask);

  if (config.season.enabled) {
    const seasonTask = cron.schedule(config.season.cron, async () => {
      try {
        await enqueueSeasonTick({ date: new Date() });
      } catch (error) {
        logger.error("scheduled season tick failed", { reason: error.message });
      }
    });
    tasks.push(seasonTask);
  }

  if (config.scheduler.runOnStart) {
    runIngestionCycle({ trigger: "startup" }).catch((error) => {
      logger.error("startup ingestion failed", { reason: error.message });
    });
  }

  logger.info("ingestion scheduler started", {
    cron: config.scheduler.cron,
    seasonEnabled: config.season.enabled,
    seasonCron: config.season.enabled ? config.season.cron : null,
  });
  return {
    stop() {
      for (const task of tasks) {
        task.stop();
      }
    },
  };
}

module.exports = {
  startScheduler,
};
