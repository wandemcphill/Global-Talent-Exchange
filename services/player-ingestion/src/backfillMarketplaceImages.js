"use strict";

const { resolvePlayerImage } = require("./imageResolver");
const logger = require("./logger");
const repository = require("./repository");
const { stableHash } = require("./hash");
const { SportmonksClient } = require("./sportmonks");
const db = require("./db");

const sportmonks = new SportmonksClient();

async function findMarketplacePlayersMissingImages({ limit }) {
  const result = await db.query(
    `
      SELECT DISTINCT
        ip.id AS app_player_id,
        ip.provider_external_id,
        ip.full_name,
        p.image_url AS existing_image_url,
        p.image_source AS existing_image_source,
        p.rights_cleared AS existing_rights_cleared
      FROM player_card_listings listing
      JOIN player_cards card ON card.id = listing.player_card_id
      JOIN ingestion_players ip ON ip.id = card.player_id
      LEFT JOIN players p ON p.player_id::text = ip.provider_external_id
      LEFT JOIN ingestion_player_image_metadata image
        ON image.player_id = ip.id
       AND image.image_role = 'portrait'
       AND image.moderation_status <> 'rejected'
      WHERE lower(listing.status) IN ('active', 'open', 'listed', 'available')
        AND (listing.expires_at IS NULL OR listing.expires_at > NOW())
        AND ip.source_provider = 'sportmonks'
        AND ip.is_real_player IS TRUE
        AND image.id IS NULL
      ORDER BY ip.full_name ASC, ip.provider_external_id ASC
      LIMIT $1
    `,
    [limit],
  );
  return result.rows;
}

async function findRemoteFallbackImages({ limit }) {
  const result = await db.query(
    `
      SELECT DISTINCT
        ip.id AS app_player_id,
        ip.provider_external_id,
        ip.full_name,
        image.id AS image_metadata_id,
        image.source_url
      FROM ingestion_player_image_metadata image
      JOIN ingestion_players ip ON ip.id = image.player_id
      JOIN player_cards card ON card.player_id = ip.id
      JOIN player_card_listings listing ON listing.player_card_id = card.id
      WHERE lower(listing.status) IN ('active', 'open', 'listed', 'available')
        AND (listing.expires_at IS NULL OR listing.expires_at > NOW())
        AND ip.source_provider = 'sportmonks'
        AND ip.is_real_player IS TRUE
        AND image.image_role = 'portrait'
        AND image.moderation_status <> 'rejected'
        AND image.rights_cleared IS TRUE
        AND image.source_url LIKE 'https://cdn.sportmonks.com/%'
      ORDER BY ip.full_name ASC, ip.provider_external_id ASC
      LIMIT $1
    `,
    [limit],
  );
  return result.rows;
}

async function upgradeRemoteFallbackImages({ limit = 2000 } = {}) {
  const rows = await findRemoteFallbackImages({ limit });
  const summary = {
    candidates: rows.length,
    upgraded: 0,
    failed: 0,
  };
  for (const row of rows) {
    try {
      const playerId = Number(row.provider_external_id);
      const resolved = resolvePlayerImage({ playerId });
      await repository.upsertAppPlayerImageMetadata({
        appPlayerId: row.app_player_id,
        playerId,
        imageUrl: resolved.imageUrl,
        storageKey: resolved.storageKey,
        rightsCleared: true,
      });
      await db.query(
        `
          UPDATE players
          SET image_url = $1,
              image_source = 'cloudinary_derived',
              updated_at = NOW()
          WHERE player_id = $2
        `,
        [resolved.imageUrl, playerId],
      );
      summary.upgraded += 1;
    } catch (error) {
      summary.failed += 1;
      logger.error("marketplace remote image upgrade failed", {
        event: "marketplace_remote_image_upgrade_failed",
        providerExternalId: row.provider_external_id,
        name: row.full_name,
        reason: error.message,
      });
    }
  }
  logger.info("marketplace remote image upgrade completed", {
    event: "marketplace_remote_image_upgrade_completed",
    ...summary,
  });
  return summary;
}

async function runBackfill({ limit = 2000, upgradeRemote = false } = {}) {
  if (upgradeRemote) {
    return upgradeRemoteFallbackImages({ limit });
  }
  const rows = await findMarketplacePlayersMissingImages({ limit });
  const summary = {
    candidates: rows.length,
    fetched: 0,
    metadataCreated: 0,
    reusedExistingImages: 0,
    uploadedOrResolved: 0,
    skippedNoImage: 0,
    failed: 0,
  };

  logger.info("marketplace image backfill started", {
    event: "marketplace_image_backfill_started",
    candidates: rows.length,
  });

  for (const [index, row] of rows.entries()) {
    try {
      const playerId = Number(row.provider_external_id);
      if (!Number.isFinite(playerId) || playerId <= 0) {
        summary.skippedNoImage += 1;
        continue;
      }

      if (row.existing_image_url && row.existing_rights_cleared) {
        const changed = await repository.upsertAppPlayerImageMetadata({
          appPlayerId: row.app_player_id,
          playerId,
          imageUrl: row.existing_image_url,
          storageKey: null,
          rightsCleared: true,
        });
        if (changed) {
          summary.metadataCreated += 1;
          summary.reusedExistingImages += 1;
        }
        continue;
      }

      const player = await sportmonks.fetchPlayerById(playerId);
      summary.fetched += 1;
      if (!player?.sportmonksImageUrl) {
        summary.skippedNoImage += 1;
        logger.warn("marketplace player skipped without sportmonks image", {
          event: "marketplace_image_backfill_skipped",
          playerId,
          name: row.full_name,
        });
        continue;
      }

      const image = resolvePlayerImage(player);
      if (!image.rightsCleared) {
        summary.skippedNoImage += 1;
        logger.warn("marketplace player image not rights-cleared", {
          event: "marketplace_image_backfill_skipped",
          playerId,
          imageSource: image.imageSource,
        });
        continue;
      }

      const playerWithHash = {
        ...player,
        sourceHash: stableHash({
          playerId: player.playerId,
          name: player.name,
          nationality: player.nationality,
          age: player.age,
          sportmonksImageUrl: player.sportmonksImageUrl,
          position: player.position,
          overall: player.overall,
          potential: player.potential,
        }),
      };
      await repository.upsertPlayer({
        ...playerWithHash,
        imageUrl: image.imageUrl,
        imageSource: image.imageSource,
        rightsCleared: image.rightsCleared,
      });
      const appPlayerId = await repository.upsertAppPlayerMirror(playerWithHash);
      const changed = await repository.upsertAppPlayerImageMetadata({
        appPlayerId: appPlayerId || row.app_player_id,
        playerId,
        imageUrl: image.imageUrl,
        storageKey: image.storageKey,
        rightsCleared: image.rightsCleared,
      });
      if (changed) {
        summary.metadataCreated += 1;
      }
      summary.uploadedOrResolved += 1;

      if ((index + 1) % 25 === 0) {
        logger.info("marketplace image backfill progress", {
          event: "marketplace_image_backfill_progress",
          processed: index + 1,
          ...summary,
        });
      }
    } catch (error) {
      summary.failed += 1;
      logger.error("marketplace image backfill failed for player", {
        event: "marketplace_image_backfill_failed",
        providerExternalId: row.provider_external_id,
        name: row.full_name,
        reason: error.message,
      });
    }
  }

  logger.info("marketplace image backfill completed", {
    event: "marketplace_image_backfill_completed",
    ...summary,
  });
  return summary;
}

if (require.main === module) {
  const limit = Number.parseInt(process.env.MARKETPLACE_IMAGE_BACKFILL_LIMIT || "2000", 10);
  const upgradeRemote = ["1", "true", "yes", "y", "on"].includes(
    String(process.env.MARKETPLACE_IMAGE_UPGRADE_REMOTE || "").toLowerCase(),
  );
  runBackfill({ limit, upgradeRemote })
    .then(async (summary) => {
      process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
      await db.close();
    })
    .catch(async (error) => {
      process.stderr.write(`${error.message}\n`);
      await db.close().catch(() => {});
      process.exitCode = 1;
    });
}

module.exports = {
  runBackfill,
};
