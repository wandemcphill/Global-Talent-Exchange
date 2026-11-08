"use strict";

const fs = require("node:fs/promises");
const path = require("node:path");
const { Pool } = require("pg");
const config = require("./config");
const logger = require("./logger");

const pool = new Pool({
  connectionString: config.databaseUrl,
  ssl: config.databaseSsl ? { rejectUnauthorized: false } : false,
});

pool.on("error", (error) => {
  logger.error("Unexpected error on idle database client", {
    event: "database_pool_error",
    reason: error.message,
  });
});

pool.on("connect", (client) => {
  client.query("SET default_transaction_read_only = off").catch((error) => {
    logger.warn("Could not set default_transaction_read_only = off on connection", {
      event: "db_read_only_reset_failed",
      reason: error.message,
    });
  });
});

async function query(sql, params = []) {
  return pool.query(sql, params);
}

async function withTransaction(callback) {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const result = await callback(client);
    await client.query("COMMIT");
    return result;
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

async function migrate() {
  const migrationsDir = path.resolve(__dirname, "..", "migrations");
  await query(`
    CREATE TABLE IF NOT EXISTS ingestion_schema_migrations (
      filename TEXT PRIMARY KEY,
      applied_at TIMESTAMP DEFAULT NOW()
    )
  `);
  const files = (await fs.readdir(migrationsDir)).filter((file) => file.endsWith(".sql")).sort();
  for (const file of files) {
    const existing = await query("SELECT 1 FROM ingestion_schema_migrations WHERE filename = $1", [
      file,
    ]);
    if (existing.rowCount > 0) {
      continue;
    }
    const sql = await fs.readFile(path.join(migrationsDir, file), "utf8");
    await withTransaction(async (client) => {
      await client.query(sql);
      await client.query("INSERT INTO ingestion_schema_migrations (filename) VALUES ($1)", [file]);
    });
    logger.info("migration applied", { file });
  }
}

async function closeDb() {
  await pool.end();
}

module.exports = {
  close: closeDb,
  migrate,
  pool,
  query,
  withTransaction,
};
