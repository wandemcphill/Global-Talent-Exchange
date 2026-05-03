"use strict";

const http = require("node:http");
const config = require("./config");
const logger = require("./logger");

function startHealthServer() {
  if (!config.health.enabled) {
    logger.info("health server disabled", { event: "health_server_disabled" });
    return null;
  }

  const server = http.createServer((request, response) => {
    if (request.method === "GET" && request.url === "/health") {
      writeJson(response, 200, {
        status: "ok",
        service: "gtex-player-ingestion",
        uptimeSeconds: Math.round(process.uptime()),
        timestamp: new Date().toISOString(),
      });
      return;
    }
    writeJson(response, 404, { status: "not_found" });
  });

  server.on("error", (error) => {
    logger.warn("health server unavailable", {
      event: "health_server_unavailable",
      reason: error.message,
    });
  });

  server.listen(config.health.port, config.health.host, () => {
    logger.info("health server listening", {
      event: "health_server_listening",
      host: config.health.host,
      port: config.health.port,
      path: "/health",
    });
  });

  return server;
}

function writeJson(response, statusCode, payload) {
  response.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
  });
  response.end(`${JSON.stringify(payload)}\n`);
}

async function closeHealthServer(server) {
  if (!server) {
    return;
  }
  await new Promise((resolve, reject) => {
    server.close((error) => {
      if (error) {
        reject(error);
        return;
      }
      resolve();
    });
  });
}

module.exports = {
  closeHealthServer,
  startHealthServer,
};
