"use strict";

const { Queue, Worker: BullWorker } = require("bullmq");
const IORedis = require("ioredis");
const config = require("./config");

if (!config.redisUrl) {
  throw new Error(
    "Player ingestion worker requires Redis. Set REDIS_URL (or GTE_REDIS_URL) and REDIS_ENABLED=true.",
  );
}

const connection = new IORedis(config.redisUrl, {
  maxRetriesPerRequest: null,
});

function createQueue(name) {
  return new Queue(name, {
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
}

const leagueQueue = createQueue(config.queues.league);
const teamQueue = createQueue(config.queues.team);
const playerQueue = createQueue(config.queues.player);
const regenQueue = createQueue(config.queues.regen);
const seasonQueue = createQueue(config.queues.season);

function createWorker(name, processor) {
  return new BullWorker(name, processor, {
    connection,
    concurrency: config.queues.concurrency,
  });
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
