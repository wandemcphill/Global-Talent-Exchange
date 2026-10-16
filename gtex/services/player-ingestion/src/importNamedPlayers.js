"use strict";

const fs = require("node:fs/promises");
const path = require("node:path");
const db = require("./db");
const { stableHash } = require("./hash");
const { resolvePlayerImage } = require("./imageResolver");
const logger = require("./logger");
const repository = require("./repository");
const { SportmonksClient, normalizePlayer } = require("./sportmonks");

const DEFAULT_INPUT_FILE = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  "tmp",
  "wonderkid_targets.txt",
);
const DEFAULT_OUTPUT_FILE = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  "tmp",
  "wonderkid_import_player_ids.txt",
);

function envInt(name, fallback, minimum = 0) {
  const raw = process.env[name];
  const parsed = raw === undefined ? fallback : Number.parseInt(String(raw), 10);
  if (!Number.isFinite(parsed) || parsed < minimum) {
    return fallback;
  }
  return parsed;
}

function envBool(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || String(raw).trim() === "") {
    return fallback;
  }
  return ["1", "true", "yes", "y", "on"].includes(String(raw).trim().toLowerCase());
}

function cleanName(value) {
  return String(value || "")
    .replace(/\([^)]*\)/g, " ")
    .replace(/\bflag\b/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function nameKey(value) {
  return cleanName(value)
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/['’`´]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
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
      logger.warn("named player import transient failure; retrying", {
        event: "named_player_import_retry",
        label,
        attempt,
        reason: error.message,
      });
      await sleep(1000 * attempt);
    }
  }
  throw lastError;
}

function parseTargetLine(line) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) {
    return null;
  }
  const [name, age, club] = trimmed.split("|").map((item) => item.trim());
  const parsedAge = Number.parseInt(age || "", 10);
  return {
    name: cleanName(name),
    expectedAge: Number.isFinite(parsedAge) ? parsedAge : null,
    club: club || null,
  };
}

async function readTargets(inputFile) {
  const raw = await fs.readFile(inputFile, "utf8");
  const seen = new Set();
  const targets = [];
  for (const line of raw.split(/\r?\n/)) {
    const target = parseTargetLine(line);
    if (!target?.name) {
      continue;
    }
    const key = nameKey(target.name);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    targets.push(target);
  }
  return targets;
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

function storePortrait(player, existing) {
  if (existing?.storage_key) {
    return {
      imageUrl: existing.source_url || null,
      storageKey: existing.storage_key,
      imageSource: "cloudinary_derived",
      rightsCleared: true,
      reused: true,
    };
  }
  return { ...resolvePlayerImage(player), reused: false };
}

async function importPlayer(player, report) {
  const normalized = withSourceHash({
    ...player,
    leagueId: player.leagueId || null,
    teamId: player.teamId || null,
    sourceProvider: "sportmonks",
    isRegen: false,
  });
  const existingAppImage = await existingAppPlayerImage(normalized.playerId);
  const portrait = await storePortrait(normalized, existingAppImage);
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

function scoreCandidate(target, candidate, options) {
  const targetKey = nameKey(target.name);
  const candidateKey = nameKey(candidate.name);
  if (!targetKey || !candidateKey) {
    return -100;
  }
  let score = 0;
  if (candidateKey === targetKey) {
    score += 100;
  } else if (candidateKey.includes(targetKey) || targetKey.includes(candidateKey)) {
    score += targetKey.length <= 4 ? 20 : 45;
  } else {
    return -100;
  }
  if (target.expectedAge !== null && candidate.age !== null && candidate.age !== undefined) {
    const delta = Math.abs(candidate.age - target.expectedAge);
    if (delta === 0) {
      score += 25;
    } else if (delta <= 1) {
      score += 10;
    } else {
      score -= 25;
    }
  }
  if (candidate.age !== null && candidate.age !== undefined) {
    if (candidate.age <= options.maxAge) {
      score += 15;
    } else {
      score -= 35;
    }
  }
  if (candidate.sportmonksImageUrl) {
    score += 5;
  }
  return score;
}

async function findCandidate(client, target, options) {
  const payload = await withRetry(`search:${target.name}`, () =>
    client.request(`/players/search/${encodeURIComponent(target.name)}`, {
      include: "country;nationality;position;detailedPosition",
      per_page: 25,
    }),
  );
  const candidates = (payload.data || []).map((item) => normalizePlayer(item));
  const scored = candidates
    .map((candidate) => ({
      candidate,
      score: scoreCandidate(target, candidate, options),
    }))
    .filter((item) => item.score >= options.minScore)
    .sort((a, b) => b.score - a.score);
  return scored[0]?.candidate || null;
}

async function writeImportedIds(outputFile, appPlayerIds) {
  await fs.mkdir(path.dirname(outputFile), { recursive: true });
  const rows = Array.from(appPlayerIds).filter(Boolean);
  await fs.writeFile(outputFile, `${rows.join("\n")}${rows.length ? "\n" : ""}`);
}

async function main() {
  const options = {
    inputFile: process.env.NAMED_PLAYER_IMPORT_FILE || DEFAULT_INPUT_FILE,
    outputFile: process.env.NAMED_PLAYER_OUTPUT_FILE || DEFAULT_OUTPUT_FILE,
    maxAge: envInt("NAMED_PLAYER_MAX_AGE", 21, 0),
    minScore: envInt("NAMED_PLAYER_MIN_SCORE", 60, 0),
    includeExistingInOutput: envBool("NAMED_PLAYER_INCLUDE_EXISTING_OUTPUT", true),
  };
  const targets = await readTargets(options.inputFile);
  const client = new SportmonksClient();
  const report = {
    targetCount: targets.length,
    matched: 0,
    notFound: [],
    ageRejected: [],
    playersImported: 0,
    playersSkippedNoImage: 0,
    playerFailures: 0,
    imagesUploaded: 0,
    imagesReused: 0,
    outputFile: options.outputFile,
  };
  const appPlayerIds = new Set();
  for (const target of targets) {
    let candidate = null;
    try {
      candidate = await findCandidate(client, target, options);
    } catch (error) {
      report.playerFailures += 1;
      logger.warn("named player search failed", {
        event: "named_player_search_failed",
        target: target.name,
        reason: error.message,
      });
      continue;
    }
    if (!candidate) {
      report.notFound.push(target.name);
      continue;
    }
    if (candidate.age !== null && candidate.age !== undefined && candidate.age > options.maxAge) {
      report.ageRejected.push({
        target: target.name,
        matchedName: candidate.name,
        age: candidate.age,
      });
      continue;
    }
    report.matched += 1;
    try {
      const appPlayerId = await importPlayer(candidate, report);
      if (appPlayerId && options.includeExistingInOutput) {
        appPlayerIds.add(appPlayerId);
      }
      logger.info("named player imported", {
        event: "named_player_imported",
        target: target.name,
        playerId: candidate.playerId,
        matchedName: candidate.name,
        age: candidate.age,
        hasImage: Boolean(candidate.sportmonksImageUrl),
      });
    } catch (error) {
      report.playerFailures += 1;
      logger.warn("named player import failed", {
        event: "named_player_import_failed",
        target: target.name,
        playerId: candidate.playerId,
        reason: error.message,
      });
    }
    await writeImportedIds(options.outputFile, appPlayerIds);
  }
  await writeImportedIds(options.outputFile, appPlayerIds);
  await repository.setSyncState("sportmonks:named-player-import");
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}

main()
  .catch((error) => {
    process.stderr.write(
      `${JSON.stringify({
        event: "named_player_import_failed",
        reason: error.message,
      })}\n`,
    );
    process.exitCode = 1;
  })
  .finally(async () => {
    await db.close();
  });
