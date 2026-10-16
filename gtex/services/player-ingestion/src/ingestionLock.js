"use strict";

const nodeCrypto = require("node:crypto");
const config = require("./config");
const logger = require("./logger");
const { connection } = require("./queues");

const releaseScript = `
  if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
  end
  return 0
`;

const extendScript = `
  if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("EXPIRE", KEYS[1], ARGV[2])
  end
  return 0
`;

async function acquireIngestionLock() {
  const token = nodeCrypto.randomUUID();
  const acquired = await connection.set(
    config.ingestion.lockKey,
    token,
    "EX",
    config.ingestion.lockTtlSeconds,
    "NX",
  );

  if (acquired !== "OK") {
    logger.info("ingestion already running, skipping", {
      event: "ingestion_lock_skipped",
      lockKey: config.ingestion.lockKey,
    });
    return null;
  }

  logger.info("ingestion lock acquired", {
    event: "ingestion_lock_acquired",
    lockKey: config.ingestion.lockKey,
    ttlSeconds: config.ingestion.lockTtlSeconds,
  });

  return {
    token,
    async extend() {
      const extended = await connection.eval(
        extendScript,
        1,
        config.ingestion.lockKey,
        token,
        String(config.ingestion.lockTtlSeconds),
      );
      if (Number(extended) !== 1) {
        throw new Error("ingestion lock was lost before it could be extended");
      }
    },
    async release() {
      const released = await connection.eval(releaseScript, 1, config.ingestion.lockKey, token);
      logger.info("ingestion lock released", {
        event: "ingestion_lock_released",
        lockKey: config.ingestion.lockKey,
        released: Number(released) === 1,
      });
    },
  };
}

module.exports = {
  acquireIngestionLock,
};
