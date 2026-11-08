"use strict";

const { Queue, Worker: BullWorker } = require("bullmq");
const IORedis = require("ioredis");
const config = require("./config");
const logger = require("./logger");
const { captureException } = require("./observability");

if (!config.redisUrl) {
  throw new Error(
    "Player ingestion worker requires Redis. Set REDIS_URL (or GTE_REDIS_URL) and REDIS_ENABLED=true.",
  );
}

const connection = new IORedis(config.redisUrl, {
  maxRetriesPerRequest: null,
});

connection.on("error", (error) => {
  logger.warn("Redis connection error", {
    event: "redis_connection_error",
    reason: error.message,
  });
});

function createQueue(name) {
  const queue = new Queue(name, {
    connection,
    defaultJobOptions: {
      attempts: 3,
      backoff: {
        type: "exponential",
        delay: 30000,
      },
      removeOnComplete: 5000,
      removeOnFail: 10000,
    },
  });

  queue.on("error", (error) => {
    logger.warn("Queue error encountered", {
      event: "queue_error",
      queue: name,
      reason: error.message,
    });
  });

  return queue;
}

const leagueQueue = createQueue(config.queues.league);
const teamQueue = createQueue(config.queues.team);
const playerQueue = createQueue(config.queues.player);
const regenQueue = createQueue(config.queues.regen);
const seasonQueue = createQueue(config.queues.season);

function createWorker(name, processor) {
  const worker = new BullWorker(name, processor, {
    connection,
    concurrency: config.queues.concurrency,
  });

  worker.on("error", (error) => {
    captureException(error, {
      tags: { queue: name },
    });
    logger.error("Worker error encountered", {
      event: "worker_error",
      queue: name,
      reason: error.message,
    });
  });

  return worker;
}

async function closeQueues(workers = []) {
  await Promise.all(workers.map((worker) => worker.close()));
  await Promise.all([
    leagueQueue.close(),
    teamQueue.close(),
    playerQueue.close(),
    regenQueue.close(),
    seasonQueue.close(),
  ]);
  await connection.quit();
}

module.exports = {
  closeQueues,
  connection,
  createWorker,
  leagueQueue,
  playerQueue,
  regenQueue,
  seasonQueue,
  teamQueue,
};
