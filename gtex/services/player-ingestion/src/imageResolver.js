"use strict";

/**
 * Canonical player image resolver for the ingestion service.
 *
 * Player images ALREADY EXIST in Cloudinary under gtex/players/{sportmonksId}.
 * This module derives public_ids and delivery URLs without any upload, download,
 * or migration. resolveAndStoreImage is the single replacement for the old
 * upload-based flow.
 */

const config = require("./config");
const logger = require("./logger");

/**
 * Return the canonical Cloudinary public_id for a player.
 * @param {string|number} sportmonksPlayerId
 */
function getPlayerPublicId(sportmonksPlayerId) {
  return `${config.cloudinary.folder}/${sportmonksPlayerId}`;
}

/**
 * Return a Cloudinary delivery URL without any upload.
 * Returns null when CLOUDINARY_CLOUD_NAME is not set.
 * @param {string|number} sportmonksPlayerId
 */
function getPlayerImageUrl(sportmonksPlayerId) {
  const cloudName =
    process.env.CLOUDINARY_CLOUD_NAME ||
    _cloudNameFromUrl(process.env.CLOUDINARY_URL);

  if (!cloudName) {
    return null;
  }

  const publicId = getPlayerPublicId(sportmonksPlayerId);
  return `https://res.cloudinary.com/${cloudName}/image/upload/f_auto,q_auto/${publicId}`;
}

function _cloudNameFromUrl(cloudinaryUrl) {
  if (!cloudinaryUrl) return null;
  try {
    const parsed = new URL(cloudinaryUrl);
    if (parsed.protocol === "cloudinary:") return parsed.hostname;
  } catch (_) {
    // ignore
  }
  return null;
}

/**
 * Replacement for the old resolveAndStoreImage.
 *
 * Derives the Cloudinary reference from the Sportmonks player ID only.
 * No network calls. No uploads. No Cloudinary credentials required.
 *
 * @param {{ playerId: string|number }} player
 */
function resolvePlayerImage(player) {
  const publicId = getPlayerPublicId(player.playerId);
  const imageUrl = getPlayerImageUrl(player.playerId);

  logger.info("image_resolved", {
    event: "image_resolved",
    playerId: player.playerId,
    publicId,
    hasUrl: Boolean(imageUrl),
  });

  return {
    imageUrl,
    storageKey: publicId,
    imageSource: "cloudinary_derived",
    rightsCleared: true,
  };
}

module.exports = {
  getPlayerPublicId,
  getPlayerImageUrl,
  resolvePlayerImage,
};
