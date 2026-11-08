"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const repositoryRoot = path.resolve(__dirname, "../../..");

test("worker startup does not attempt schema migrations", () => {
  const entrypoint = fs.readFileSync(
    path.join(repositoryRoot, "services/player-ingestion/src/index.js"),
    "utf8",
  );

  assert.doesNotMatch(entrypoint, /\bdb\.migrate\s*\(/);
});

test("Render runs idempotent migrations before starting the ingestion worker", () => {
  const blueprint = fs.readFileSync(path.join(repositoryRoot, "render.yaml"), "utf8");
  const serviceStart = blueprint.indexOf("  - name: gtex-player-ingestion-worker");
  assert.notEqual(serviceStart, -1);

  const nextService = blueprint.indexOf("\n  - name:", serviceStart + 1);
  const workerService = blueprint.slice(
    serviceStart,
    nextService === -1 ? blueprint.length : nextService,
  );
  const migrationCommand = workerService.indexOf("preDeployCommand:");
  const startCommand = workerService.indexOf("startCommand:");

  assert.notEqual(migrationCommand, -1);
  assert.notEqual(startCommand, -1);
  assert.ok(migrationCommand < startCommand);
  assert.match(workerService, /npm run migrate/);
  assert.match(workerService, /default_transaction_read_only=off/);
});

test("Render environment sets PGOPTIONS for transaction write capability", () => {
  const blueprint = fs.readFileSync(path.join(repositoryRoot, "render.yaml"), "utf8");
  const serviceStart = blueprint.indexOf("  - name: gtex-player-ingestion-worker");
  assert.notEqual(serviceStart, -1);

  const nextService = blueprint.indexOf("\n  - name:", serviceStart + 1);
  const workerService = blueprint.slice(
    serviceStart,
    nextService === -1 ? blueprint.length : nextService,
  );

  assert.match(workerService, /key:\s*PGOPTIONS/);
  assert.match(workerService, /value:\s*"-c default_transaction_read_only=off"/);
});

test("database pool registers error and read-only reset handlers", () => {
  const dbSrc = fs.readFileSync(
    path.join(repositoryRoot, "services/player-ingestion/src/db.js"),
    "utf8",
  );

  assert.match(dbSrc, /pool\.on\("error"/);
  assert.match(dbSrc, /pool\.on\("connect"/);
  assert.match(dbSrc, /SET default_transaction_read_only = off/);
});

test("queues module registers error listeners on Redis connection, queues, and workers", () => {
  const queuesSrc = fs.readFileSync(
    path.join(repositoryRoot, "services/player-ingestion/src/queues.js"),
    "utf8",
  );

  assert.match(queuesSrc, /connection\.on\("error"/);
  assert.match(queuesSrc, /queue\.on\("error"/);
  assert.match(queuesSrc, /worker\.on\("error"/);
});

test("the worker package exposes the Node built-in test runner", () => {
  const packageJson = JSON.parse(
    fs.readFileSync(path.join(repositoryRoot, "services/player-ingestion/package.json"), "utf8"),
  );

  assert.equal(packageJson.scripts.test, "node --test");
});
