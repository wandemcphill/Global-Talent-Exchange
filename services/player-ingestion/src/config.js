"use strict";

const path = require("node:path");
const dotenv = require("dotenv");

dotenv.config({
  path: process.env.INGESTION_ENV_FILE || path.resolve(__dirname, "..", ".env"),
});

function env(name, fallback = undefined) {
  const value = process.env[name];
  if (value === undefined || String(value).trim() === "") {
    return fallback;
  }
  return String(value).trim();
}

function required(name) {
  const value = env(name);
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

function requiredAny(names) {
  for (const name of names) {
    const value = env(name);
    if (value) {
      return value;
    }
  }
  throw new Error(`${names.join(" or ")} is required`);
}

function boolEnv(name, fallback) {
  const value = env(name);
  if (value === undefined) {
    return fallback;
  }
  return ["1", "true", "yes", "y", "on"].includes(value.toLowerCase());
}

function intEnv(name, fallback, minimum = 0) {
  const raw = env(name);
  const parsed = raw === undefined ? fallback : Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < minimum) {
    return fallback;
  }
  return parsed;
}

function listEnv(name) {
  return env(name, "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function transferWindowsEnv(name, fallback) {
  const raw = env(name, fallback);
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item) => {
      const [start, end] = item.split(":").map((value) => value.trim());
      return { start, end };
    })
    .filter((window) => window.start && window.end);
}

function databaseSslDefault() {
  const url = env("DATABASE_URL", "");
  return (
    !url.includes("localhost") &&
    !url.includes("127.0.0.1") &&
    !url.startsWith("postgres://postgres@")
  );
}

module.exports = {
  databaseUrl: required("DATABASE_URL"),
  databaseSsl: boolEnv("DATABASE_SSL", databaseSslDefault()),
  redisUrl: requiredAny(["REDIS_URL", "GTE_REDIS_URL"]),
  sportmonks: {
    baseUrl: env("SPORTMONKS_BASE_URL", "https://api.sportmonks.com/v3/football").replace(
      /\/+$/,
      "",
    ),
    apiToken: required("SPORTMONKS_API_TOKEN"),
    pageSize: intEnv("SPORTMONKS_PAGE_SIZE", 50, 1),
    timeoutMs: intEnv("SPORTMONKS_TIMEOUT_MS", 20000, 1000),
    rateLimitMs: intEnv("SPORTMONKS_REQUEST_SPACING_MS", 1200, 0),
    updatedSinceSupported: boolEnv("SPORTMONKS_UPDATED_SINCE_SUPPORTED", false),
    leagueIds: listEnv("SPORTMONKS_LEAGUE_IDS"),
  },
  cloudinary: {
    folder: env("CLOUDINARY_PLAYER_FOLDER", "gtex/players"),
  },
  audio: {
    commentaryEnabled: boolEnv("AUDIO_COMMENTARY_ENABLED", false),
    elevenLabsApiKey: env("ELEVENLABS_API_KEY", ""),
    elevenLabsVoiceId: env("ELEVENLABS_VOICE_ID", ""),
  },
  environment: env("NODE_ENV", "production"),
  health: {
    enabled: boolEnv("HEALTH_SERVER_ENABLED", true),
    host: env("HEALTH_HOST", "0.0.0.0"),
    port: intEnv("HEALTH_PORT", intEnv("PORT", 3000, 1), 1),
  },
  ingestion: {
    idleGraceMs: intEnv("INGESTION_IDLE_GRACE_MS", 5000, 1000),
    lockKey: env("INGESTION_LOCK_KEY", "ingestion_lock"),
    lockTtlSeconds: intEnv("INGESTION_LOCK_TTL_SECONDS", 3600, 60),
    queuePollMs: intEnv("INGESTION_QUEUE_POLL_MS", 5000, 1000),
    runTimeoutSeconds: intEnv("INGESTION_RUN_TIMEOUT_SECONDS", 3300, 60),
  },
  wikimedia: {
    enabled: boolEnv("WIKIMEDIA_FALLBACK_ENABLED", true),
    rightsClearedDefault: boolEnv("WIKIMEDIA_RIGHTS_CLEARED_DEFAULT", false),
    userAgent: env("WIKIMEDIA_USER_AGENT", "GTEXPlayerIngestion/0.1"),
  },
  regen: {
    youthPlayersPerLeague: intEnv("GTEX_REGENS_PER_LEAGUE", 3, 0),
  },
  queues: {
    league: "gtex-ingestion-league",
    team: "gtex-ingestion-team",
    player: "gtex-ingestion-player",
    regen: "gtex-ingestion-regen",
    season: "gtex-season-engine",
    concurrency: intEnv("INGESTION_WORKER_CONCURRENCY", 4, 1),
  },
  scheduler: {
    cron: env("INGESTION_CRON", "0 */6 * * *"),
    runOnStart: boolEnv("INGESTION_RUN_ON_START", true),
  },
  season: {
    enabled: boolEnv("SEASON_ENGINE_ENABLED", false),
    cron: env("SEASON_CRON", "15 0 * * *"),
    fixturesPerDay: intEnv("SEASON_FIXTURES_PER_DAY", 1, 1),
    regenPerSeason: intEnv("SEASON_REGENS_PER_SEASON", 12, 0),
    transfersEnabled: boolEnv("SEASON_TRANSFERS_ENABLED", false),
    transferLimitPerTick: intEnv("SEASON_TRANSFER_LIMIT_PER_TICK", 1, 0),
    transferWindows: transferWindowsEnv(
      "SEASON_TRANSFER_WINDOWS",
      "2026-01-01:2026-01-31,2026-08-01:2026-08-31",
    ),
  },
};
