"use strict";

const config = require("./config");
const logger = require("./logger");
const { captureException } = require("./observability");
const { seasonQueue } = require("./queues");
const { runMatchday } = require("./seasonEngine");

async function enqueueSeasonTick({ date = new Date(), runId = toDateKey(date) } = {}) {
  if (!config.season.enabled) {
    logger.info("season engine disabled; tick skipped", {
      event: "season_tick_skipped",
      reason: "disabled",
    });
    return { queued: false };
  }
  const dateKey = toDateKey(date);
  await seasonQueue.add(
    "run-matchday",
    {
      date: dateKey,
    },
    { jobId: `season:matchday:${dateKey}:${runId}` },
  );
  logger.info("season matchday queued", {
    event: "season_matchday_queued",
    date: dateKey,
  });
  return { queued: true, date: dateKey };
}

async function processSeasonJob(job) {
  if (job.name === "run-matchday") {
    return runMatchday(job.data?.date || new Date());
  }
  throw new Error(`Unknown season job: ${job.name}`);
}

function attachSeasonWorkerLogging(worker) {
  worker.on("failed", (job, error) => {
    captureException(error, {
      tags: { queue: worker.name },
      extra: { jobId: job?.id, jobName: job?.name },
    });
    logger.error("season job failed", {
      event: "season_job_failed",
      queue: worker.name,
      jobId: job?.id,
      reason: error.message,
    });
  });
}

function toDateKey(value) {
  return new Date(value).toISOString().slice(0, 10);
}

module.exports = {
  attachSeasonWorkerLogging,
  enqueueSeasonTick,
  processSeasonJob,
};
