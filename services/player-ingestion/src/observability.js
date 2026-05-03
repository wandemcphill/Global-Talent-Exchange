"use strict";

const config = require("./config");
const logger = require("./logger");

let sentry = null;

function initObservability() {
  if (!process.env.SENTRY_DSN) {
    logger.info("sentry disabled", { event: "sentry_disabled" });
    return;
  }

  sentry = require("@sentry/node");
  sentry.init({
    dsn: process.env.SENTRY_DSN,
    environment: config.environment,
    tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE || 0),
  });
  logger.info("sentry enabled", {
    event: "sentry_enabled",
    environment: config.environment,
  });
}

function captureException(error, context = {}) {
  if (!sentry) {
    return;
  }
  sentry.withScope((scope) => {
    for (const [key, value] of Object.entries(context.tags || {})) {
      scope.setTag(key, value);
    }
    for (const [key, value] of Object.entries(context.extra || {})) {
      scope.setExtra(key, value);
    }
    sentry.captureException(error);
  });
}

async function closeObservability(timeoutMs = 2000) {
  if (sentry) {
    await sentry.close(timeoutMs);
  }
}

module.exports = {
  captureException,
  closeObservability,
  initObservability,
};
