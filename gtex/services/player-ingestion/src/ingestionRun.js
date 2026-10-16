"use strict";

const config = require("./config");
const { enqueueLeagues } = require("./jobs");
const { acquireIngestionLock } = require("./ingestionLock");
const logger = require("./logger");
const { captureException } = require("./observability");
const { leagueQueue, playerQueue, regenQueue, teamQueue } = require("./queues");
const repository = require("./repository");

const trackedQueues = [
  ["league", leagueQueue],
  ["team", teamQueue],
  ["player", playerQueue],
  ["regen", regenQueue],
];

async function runIngestionCycle({ trigger = "manual", waitForIdle = true } = {}) {
  const lock = await acquireIngestionLock();
  if (!lock) {
    return { status: "skipped" };
  }

  const startedAt = Date.now();
  let lockRefresh = null;
  try {
    lockRefresh = startLockRefresh(lock);
    logger.info("ingestion cycle started", {
      event: "ingestion_cycle_started",
      trigger,
      waitForIdle,
    });

    const enqueueResult = await enqueueLeagues();
    if (waitForIdle) {
      await waitForQueuesIdle();
    }

    await repository.setSyncState("players");
    logger.info("ingestion cycle completed", {
      event: "ingestion_cycle_completed",
      trigger,
      durationMs: Date.now() - startedAt,
      ...enqueueResult,
    });
    return { status: "completed" };
  } catch (error) {
    captureException(error, { tags: { trigger }, extra: { phase: "ingestion_cycle" } });
    logger.error("ingestion cycle failed", {
      event: "ingestion_cycle_failed",
      trigger,
      reason: error.message,
    });
    throw error;
  } finally {
    if (lockRefresh) {
      clearInterval(lockRefresh);
    }
    await lock.release().catch((error) => {
      captureException(error, { extra: { phase: "ingestion_lock_release" } });
      logger.error("ingestion lock release failed", {
        event: "ingestion_lock_release_failed",
        reason: error.message,
      });
    });
  }
}

function startLockRefresh(lock) {
  const refreshMs = Math.max(5000, Math.floor((config.ingestion.lockTtlSeconds * 1000) / 2));
  return setInterval(() => {
    lock.extend().catch((error) => {
      captureException(error, { extra: { phase: "ingestion_lock_extend" } });
      logger.error("ingestion lock refresh failed", {
        event: "ingestion_lock_refresh_failed",
        reason: error.message,
      });
    });
  }, refreshMs);
}

async function waitForQueuesIdle() {
  const timeoutAt = Date.now() + config.ingestion.runTimeoutSeconds * 1000;
  let idleSince = null;

  while (Date.now() < timeoutAt) {
    const counts = await getQueueCounts();
    const pending = counts.reduce((total, queue) => total + queue.pending, 0);

    if (pending === 0) {
      idleSince ??= Date.now();
      if (Date.now() - idleSince >= config.ingestion.idleGraceMs) {
        logger.info("ingestion queues idle", {
          event: "ingestion_queues_idle",
          counts,
        });
        return;
      }
    } else {
      idleSince = null;
      logger.info("ingestion queues still active", {
        event: "ingestion_queues_active",
        counts,
      });
    }

    await sleep(config.ingestion.queuePollMs);
  }

  throw new Error(
    `ingestion queues did not become idle within ${config.ingestion.runTimeoutSeconds}s`,
  );
}

async function getQueueCounts() {
  return Promise.all(
    trackedQueues.map(async ([name, queue]) => {
      const counts = await queue.getJobCounts(
        "waiting",
        "active",
        "delayed",
        "prioritized",
        "waiting-children",
      );
      return {
        name,
        ...counts,
        pending:
          Number(counts.waiting || 0) +
          Number(counts.active || 0) +
          Number(counts.delayed || 0) +
          Number(counts.prioritized || 0) +
          Number(counts["waiting-children"] || 0),
      };
    }),
  );
}

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

module.exports = {
  runIngestionCycle,
};
