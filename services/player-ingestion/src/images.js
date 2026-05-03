"use strict";

const axios = require("axios");
const cloudinary = require("cloudinary").v2;
const config = require("./config");
const logger = require("./logger");

configureCloudinary();

function hasCloudinaryConfig() {
  return Boolean(
    process.env.CLOUDINARY_URL ||
    (process.env.CLOUDINARY_CLOUD_NAME &&
      process.env.CLOUDINARY_API_KEY &&
      process.env.CLOUDINARY_API_SECRET),
  );
}

function configureCloudinary() {
  if (process.env.CLOUDINARY_URL) {
    try {
      const parsed = new URL(process.env.CLOUDINARY_URL);
      if (parsed.protocol === "cloudinary:") {
        cloudinary.config({
          cloud_name: parsed.hostname,
          api_key: decodeURIComponent(parsed.username),
          api_secret: decodeURIComponent(parsed.password),
          secure: true,
        });
        return;
      }
    } catch (error) {
      logger.warn("cloudinary url parse failed", {
        event: "cloudinary_config_failed",
        reason: error.message,
      });
    }
  }
  if (
    process.env.CLOUDINARY_CLOUD_NAME &&
    process.env.CLOUDINARY_API_KEY &&
    process.env.CLOUDINARY_API_SECRET
  ) {
    cloudinary.config({
      cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
      api_key: process.env.CLOUDINARY_API_KEY,
      api_secret: process.env.CLOUDINARY_API_SECRET,
      secure: true,
    });
  }
}

async function resolveAndStoreImage(player, options = {}) {
  const allowAiFallback = options.allowAiFallback ?? true;
  const candidates = [];
  if (player.sportmonksImageUrl) {
    candidates.push({
      source: "sportmonks",
      url: player.sportmonksImageUrl,
      rightsCleared: true,
    });
  }

  const wikimediaUrl = await findWikimediaImage(player).catch((error) => {
    logger.warn("wikimedia lookup failed", { playerId: player.playerId, reason: error.message });
    return null;
  });
  if (wikimediaUrl) {
    candidates.push({
      source: "wikimedia",
      url: wikimediaUrl,
      rightsCleared: config.wikimedia.rightsClearedDefault,
    });
  }

  if (allowAiFallback) {
    candidates.push({
      source: "ai_generated",
      url: getAiFaceUrl(player),
      rightsCleared: true,
    });
  }

  if (!hasCloudinaryConfig()) {
    logger.warn("cloudinary missing, using remote image fallback", {
      event: "image_storage_unavailable",
      playerId: player.playerId,
    });
    return remoteFallback(candidates);
  }

  let fallback = null;
  for (const candidate of candidates) {
    try {
      const uploaded = await uploadRemoteImage(candidate.url, player.playerId, candidate.source);
      return {
        imageUrl: uploaded.secure_url,
        storageKey: uploaded.public_id,
        imageSource: candidate.source,
        rightsCleared: candidate.rightsCleared,
      };
    } catch (error) {
      fallback ??= remoteFallback([candidate]);
      logger.warn("image candidate failed", {
        event: "image_candidate_failed",
        playerId: player.playerId,
        source: candidate.source,
        reason: error.message,
      });
    }
  }

  if (fallback.imageUrl) {
    logger.warn("using remote image fallback after storage failures", {
      event: "image_remote_fallback_used",
      playerId: player.playerId,
      imageSource: fallback.imageSource,
    });
    return fallback;
  }

  return {
    imageUrl: null,
    storageKey: null,
    imageSource: "missing",
    rightsCleared: false,
  };
}

function remoteFallback(candidates) {
  const candidate = candidates.find(
    (item) => item.url && item.source !== "ai_generated" && item.rightsCleared,
  );
  if (!candidate) {
    return {
      imageUrl: null,
      imageSource: "missing",
      rightsCleared: false,
    };
  }
  return {
    imageUrl: candidate.url,
    storageKey: null,
    imageSource: `${candidate.source}_remote_fallback`,
    rightsCleared: candidate.rightsCleared,
  };
}

async function uploadRemoteImage(url, playerId, source) {
  return cloudinary.uploader.upload(url, {
    folder: config.cloudinary.folder,
    public_id: String(playerId),
    overwrite: true,
    resource_type: "image",
    tags: ["gtex", "player", source],
    context: {
      player_id: String(playerId),
      source,
    },
  });
}

async function findWikimediaImage(player) {
  if (!config.wikimedia.enabled || !player.name) {
    return null;
  }
  const response = await axios.get("https://en.wikipedia.org/w/api.php", {
    timeout: 10000,
    headers: {
      "User-Agent": config.wikimedia.userAgent,
    },
    params: {
      action: "query",
      format: "json",
      generator: "search",
      gsrsearch: `${player.name} footballer`,
      prop: "pageimages",
      piprop: "original",
      origin: "*",
      gsrlimit: 3,
    },
  });
  const pages = response.data?.query?.pages || {};
  for (const page of Object.values(pages)) {
    if (page?.original?.source) {
      return page.original.source;
    }
  }
  return null;
}

function getAiFaceUrl(player) {
  const seed = encodeURIComponent(`${player.playerId}`);
  return `https://thispersondoesnotexist.com/image?gtex_seed=${seed}`;
}

module.exports = {
  uploadRemoteImage,
  resolveAndStoreImage,
};
