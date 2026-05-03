"use strict";

const fs = require("node:fs/promises");
const path = require("node:path");
const db = require("./db");
const { stableHash } = require("./hash");
const { uploadRemoteImage } = require("./images");
const logger = require("./logger");
const repository = require("./repository");
const { SportmonksClient, normalizePlayer } = require("./sportmonks");

const DEFAULT_OUTPUT_FILE = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  "tmp",
  "youth_import_player_ids.txt",
);

function envBool(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || String(raw).trim() === "") {
    return fallback;
  }
  return ["1", "true", "yes", "y", "on"].includes(String(raw).trim().toLowerCase());
}

function envInt(name, fallback, minimum = 0) {
  const raw = process.env[name];
  const parsed = raw === undefined ? fallback : Number.parseInt(String(raw), 10);
  if (!Number.isFinite(parsed) || parsed < minimum) {
    return fallback;
  }
  return parsed;
}

function listEnv(name) {
  return (process.env[name] || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function countryKey(value) {
  const normalized = String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
  if (normalized === "turkiye" || normalized === "turkey") {
    return "turkey";
  }
  return normalized;
}

function youthOptions() {
  return {
    minAge: envInt("YOUTH_IMPORT_MIN_AGE", 14, 1),
    maxAge: envInt("YOUTH_IMPORT_MAX_AGE", 21, 1),
    startPage: envInt("YOUTH_IMPORT_START_PAGE", 1, 1),
    maxPages: envInt("YOUTH_IMPORT_MAX_PAGES", 400, 0),
    pageSize: envInt("YOUTH_IMPORT_PAGE_SIZE", 50, 1),
    targetCount: envInt("YOUTH_IMPORT_TARGET_COUNT", 1000, 0),
    countries: listEnv("YOUTH_IMPORT_COUNTRIES").map(countryKey),
    requireSportmonksImage: envBool("YOUTH_IMPORT_REQUIRE_SPORTMONKS_IMAGE", true),
    includeExistingInOutput: envBool("YOUTH_IMPORT_INCLUDE_EXISTING_OUTPUT", false),
    outputFile: process.env.YOUTH_IMPORT_OUTPUT_FILE || DEFAULT_OUTPUT_FILE,
  };
}

function withSourceHash(player) {
  return {
    ...player,
    sourceHash:
      player.sourceHash ||
      stableHash({
        playerId: player.playerId,
        name: player.name,
        nationality: player.nationality,
        age: player.age,
        sportmonksImageUrl: player.sportmonksImageUrl,
        leagueId: player.leagueId,
        teamId: player.teamId,
        isRegen: player.isRegen,
        position: player.position,
        overall: player.overall,
        potential: player.potential,
        pace: player.pace,
        shooting: player.shooting,
        passing: player.passing,
        dribbling: player.dribbling,
        defending: player.defending,
        physical: player.physical,
        traits: player.traits,
        personality: player.personality,
      }),
  };
}

async function sleep(ms) {
  await new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function withRetry(label, callback, attempts = 3) {
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await callback();
    } catch (error) {
      lastError = error;
      if (attempt >= attempts) {
        break;
      }
      logger.warn("youth import transient failure; retrying", {
        event: "youth_import_retry",
        label,
        attempt,
        reason: error.message,
      });
      await sleep(1000 * attempt);
    }
  }
  throw lastError;
}

async function existingProviderIds(playerIds) {
  if (!playerIds.length) {
    return new Map();
  }
  const result = await withRetry("existing-provider-ids", () =>
    db.query(
      `
      SELECT p.player_id::text AS player_id, ip.id AS app_player_id
      FROM players p
      LEFT JOIN ingestion_players ip
        ON ip.source_provider = 'sportmonks'
       AND ip.provider_external_id = p.player_id::text
      WHERE p.player_id = ANY($1::bigint[])
      UNION
      SELECT provider_external_id AS player_id, id AS app_player_id
      FROM ingestion_players
      WHERE source_provider = 'sportmonks'
        AND provider_external_id = ANY($2::text[])
    `,
      [playerIds, playerIds.map(String)],
    ),
  );
  return new Map(result.rows.map((row) => [String(row.player_id), row.app_player_id || null]));
}

async function existingAppPlayerImage(playerId) {
  const result = await withRetry(`existing-app-image:${playerId}`, () =>
    db.query(
      `
      SELECT ip.id AS app_player_id, ipim.source_url, ipim.storage_key
      FROM ingestion_players ip
      LEFT JOIN ingestion_player_image_metadata ipim
        ON ipim.player_id = ip.id
       AND ipim.image_role = 'portrait'
       AND ipim.moderation_status = 'approved'
       AND ipim.rights_cleared IS TRUE
      WHERE ip.source_provider = 'sportmonks'
        AND ip.provider_external_id = $1
      LIMIT 1
    `,
      [String(playerId)],
    ),
  );
  return result.rows[0] || null;
}

async function storePortrait(player, existing) {
  if (existing?.source_url && existing?.storage_key) {
    return {
      imageUrl: existing.source_url,
      storageKey: existing.storage_key,
      imageSource: "sportmonks",
      rightsCleared: true,
      reused: true,
    };
  }
  if (!player.sportmonksImageUrl) {
    return {
      imageUrl: null,
      storageKey: null,
      imageSource: "missing",
      rightsCleared: false,
      reused: false,
    };
  }
  const uploaded = await withRetry(`portrait:${player.playerId}`, () =>
    uploadRemoteImage(player.sportmonksImageUrl, player.playerId, "sportmonks"),
  );
  return {
    imageUrl: uploaded.secure_url,
    storageKey: uploaded.public_id,
    imageSource: "sportmonks",
    rightsCleared: true,
    reused: false,
  };
}

async function importYouthPlayer(player, report) {
  const normalized = withSourceHash({
    ...player,
    leagueId: null,
    teamId: null,
    sourceProvider: "sportmonks",
    isRegen: false,
  });
  const existingAppImage = await existingAppPlayerImage(normalized.playerId);
  let portrait;
  try {
    portrait = await storePortrait(normalized, existingAppImage);
  } catch (error) {
    report.imageFailures += 1;
    logger.warn("youth portrait upload failed", {
      event: "youth_portrait_failed",
      playerId: normalized.playerId,
      reason: error.message,
    });
    return null;
  }
  if (!portrait.imageUrl || !portrait.rightsCleared) {
    report.playersSkippedNoImage += 1;
    return null;
  }
  await withRetry(`upsert-player:${normalized.playerId}`, () =>
    repository.upsertPlayer({
      ...normalized,
      imageUrl: portrait.imageUrl,
      imageSource: portrait.imageSource,
      rightsCleared: portrait.rightsCleared,
    }),
  );
  const appPlayerId =
    existingAppImage?.app_player_id ||
    (await withRetry(`upsert-app-player:${normalized.playerId}`, () =>
      repository.upsertAppPlayerMirror(normalized),
    ));
  await withRetry(`upsert-player-image:${normalized.playerId}`, () =>
    repository.upsertAppPlayerImageMetadata({
      appPlayerId,
      playerId: normalized.playerId,
      imageUrl: portrait.imageUrl,
      storageKey: portrait.storageKey,
      rightsCleared: portrait.rightsCleared,
    }),
  );
  report.playersImported += 1;
  if (portrait.reused) {
    report.imagesReused += 1;
  } else {
    report.imagesUploaded += 1;
  }
  return appPlayerId;
}

function inAgeBand(player, options) {
  return player.age >= options.minAge && player.age <= options.maxAge;
}

function inCountryScope(player, options) {
  if (!options.countries.length) {
    return true;
  }
  return options.countries.includes(countryKey(player.nationality));
}

async function writeImportedIds(outputFile, appPlayerIds) {
  await fs.mkdir(path.dirname(outputFile), { recursive: true });
  const rows = Array.from(appPlayerIds).filter(Boolean);
  await fs.writeFile(outputFile, `${rows.join("\n")}${rows.length ? "\n" : ""}`);
}

async function importYouthPlayers() {
  const options = youthOptions();
  if (options.minAge > options.maxAge) {
    throw new Error("YOUTH_IMPORT_MIN_AGE cannot be greater than YOUTH_IMPORT_MAX_AGE");
  }
  const client = new SportmonksClient();
  const report = {
    ageBand: `${options.minAge}-${options.maxAge}`,
    startPage: options.startPage,
    lastPageScanned: options.startPage - 1,
    pageSize: options.pageSize,
    maxPages: options.maxPages,
    targetCount: options.targetCount,
    countries: options.countries,
    includeExistingInOutput: options.includeExistingInOutput,
    playersSeen: 0,
    youthSeen: 0,
    playersSkippedExisting: 0,
    playersSkippedNoImage: 0,
    playersImported: 0,
    playerFailures: 0,
    imagesUploaded: 0,
    imagesReused: 0,
    imageFailures: 0,
    pageFailures: 0,
    outputFile: options.outputFile,
  };
  const importedAppPlayerIds = new Set();
  let page = options.startPage;
  let pagesScanned = 0;
  for (;;) {
    if (options.maxPages > 0 && pagesScanned >= options.maxPages) {
      break;
    }
    if (options.targetCount > 0 && report.playersImported >= options.targetCount) {
      break;
    }
    let payload;
    try {
      payload = await withRetry(`players-page:${page}`, () =>
        client.request("/players", {
          include: "country;nationality;position;detailedPosition",
          order: "desc",
          page,
          per_page: options.pageSize,
        }),
      );
    } catch (error) {
      report.pageFailures += 1;
      logger.warn("youth player page failed; ending partial import", {
        event: "youth_player_page_failed",
        page,
        reason: error.message,
      });
      break;
    }
    const players = (payload.data || []).map((item) => normalizePlayer(item));
    if (!players.length) {
      break;
    }
    pagesScanned += 1;
    report.lastPageScanned = page;
    report.playersSeen += players.length;
    const youthPlayers = players.filter(
      (player) => inAgeBand(player, options) && inCountryScope(player, options),
    );
    report.youthSeen += youthPlayers.length;
    const existingIds = await existingProviderIds(youthPlayers.map((player) => player.playerId));
    let pageImported = 0;
    for (const player of youthPlayers) {
      if (options.targetCount > 0 && report.playersImported >= options.targetCount) {
        break;
      }
      if (existingIds.has(String(player.playerId))) {
        report.playersSkippedExisting += 1;
        if (options.includeExistingInOutput) {
          importedAppPlayerIds.add(existingIds.get(String(player.playerId)));
        }
        continue;
      }
      if (options.requireSportmonksImage && !player.sportmonksImageUrl) {
        report.playersSkippedNoImage += 1;
        continue;
      }
      let appPlayerId = null;
      try {
        appPlayerId = await importYouthPlayer(player, report);
      } catch (error) {
        report.playerFailures += 1;
        logger.warn("youth player import failed; continuing", {
          event: "youth_player_import_failed",
          playerId: player.playerId,
          reason: error.message,
        });
      }
      if (appPlayerId) {
        importedAppPlayerIds.add(appPlayerId);
        pageImported += 1;
      }
    }
    logger.info("youth player page scanned", {
      event: "youth_player_page_scanned",
      page,
      playersSeen: players.length,
      youthSeen: youthPlayers.length,
      imported: pageImported,
      totalImported: report.playersImported,
    });
    await writeImportedIds(options.outputFile, importedAppPlayerIds);
    if (!payload.pagination?.has_more) {
      break;
    }
    page += 1;
  }
  await writeImportedIds(options.outputFile, importedAppPlayerIds);
  await repository.setSyncState("sportmonks:youth-import");
  return report;
}

importYouthPlayers()
  .then((report) => {
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  })
  .catch((error) => {
    process.stderr.write(
      `${JSON.stringify({
        event: "youth_import_failed",
        reason: error.message,
      })}\n`,
    );
    process.exitCode = 1;
  })
  .finally(async () => {
    await db.close();
  });
