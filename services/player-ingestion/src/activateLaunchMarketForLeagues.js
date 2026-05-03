"use strict";

const fs = require("fs");
const { randomUUID } = require("crypto");
const { Pool } = require("pg");
const config = require("./config");

const DEFAULT_MARKET_MAKER_USER_ID = "48d51599-ff94-4545-ad9a-6dd5162c42be";
const LAUNCH_REAL_TIER_CODE = "launch_real";
const LAUNCH_EDITION_CODE = "launch_2026";

function parseLeagueIds() {
  return (process.env.LAUNCH_MARKET_LEAGUE_IDS || process.env.LAUNCH_LEAGUE_IDS || "")
    .split(",")
    .map((item) => Number.parseInt(item.trim(), 10))
    .filter((item) => Number.isFinite(item) && item > 0);
}

function parsePlayerIds() {
  const path = process.env.LAUNCH_MARKET_PLAYER_ID_FILE;
  if (!path) {
    return [];
  }
  return fs
    .readFileSync(path, "utf8")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

async function ensureTier(client) {
  const existing = await client.query("SELECT id FROM player_card_tiers WHERE code = $1", [
    LAUNCH_REAL_TIER_CODE,
  ]);
  if (existing.rowCount) {
    return existing.rows[0].id;
  }
  const id = randomUUID();
  await client.query(
    `
      INSERT INTO player_card_tiers (
        id, code, name, rarity_rank, max_supply, supply_multiplier,
        base_mint_price_credits, color_hex, is_active, metadata_json,
        created_at, updated_at
      )
      VALUES (
        $1::text, $2::text, 'Launch Real Player', 25, NULL, 1.0, 0, '#2FB344', TRUE,
        '{"source":"launch_market_league_activation"}',
        NOW(), NOW()
      )
    `,
    [id, LAUNCH_REAL_TIER_CODE],
  );
  return id;
}

async function loadScopedPlayers(client, tierId, leagueIds, playerIds) {
  if (!leagueIds.length && !playerIds.length) {
    throw new Error(
      "LAUNCH_MARKET_LEAGUE_IDS, LAUNCH_LEAGUE_IDS, or LAUNCH_MARKET_PLAYER_ID_FILE is required",
    );
  }
  const filters = [];
  const params = [tierId, LAUNCH_EDITION_CODE];
  if (leagueIds.length) {
    params.push(leagueIds);
    filters.push(`p.league_id = ANY($${params.length}::bigint[])`);
  }
  if (playerIds.length) {
    params.push(playerIds);
    filters.push(`ip.id = ANY($${params.length}::text[])`);
  }
  const whereScope = filters.length ? `AND (${filters.join(" OR ")})` : "";
  const result = await client.query(
    `
      SELECT
        ip.id AS player_id,
        COALESCE(ip.canonical_display_name, ip.full_name) AS display_name,
        GREATEST(COALESCE(ps.current_value_credits, ip.current_market_reference_value, 25), 25)::numeric(18,4)
          AS sale_price,
        GREATEST(COALESCE(ps.current_value_credits, ip.current_market_reference_value, 25) * 0.08, 5)::numeric(18,4)
          AS loan_fee,
        pc.id AS existing_card_id
      FROM ingestion_players ip
      JOIN players p ON p.player_id::text = ip.provider_external_id
      JOIN ingestion_player_image_metadata pim
        ON pim.player_id = ip.id
       AND pim.image_role = 'portrait'
       AND pim.moderation_status = 'approved'
       AND pim.rights_cleared IS TRUE
       AND pim.source_url IS NOT NULL
      LEFT JOIN player_summary_read_models ps ON ps.player_id = ip.id
      LEFT JOIN player_cards pc
        ON pc.player_id = ip.id
       AND pc.tier_id = $1::text
       AND pc.edition_code = $2::text
      WHERE ip.source_provider = 'sportmonks'
        AND ip.is_real_player IS TRUE
        AND ip.is_tradable IS TRUE
        ${whereScope}
      ORDER BY p.league_id, ip.full_name
    `,
    params,
  );
  return result.rows.map((row) => {
    const cardId = row.existing_card_id || randomUUID();
    return {
      player_id: row.player_id,
      card_id: cardId,
      is_new_card: !row.existing_card_id,
      display_name: row.display_name,
      sale_price: row.sale_price,
      loan_fee: row.loan_fee,
      supply_batch_id: randomUUID(),
      history_id: randomUUID(),
      holding_id: randomUUID(),
      sale_listing_row_id: randomUUID(),
      sale_listing_public_id: randomUUID(),
      loan_listing_id: randomUUID(),
    };
  });
}

async function activateMarket(client, rows, tierId, marketMakerUserId) {
  await client.query(`
    CREATE TEMP TABLE tmp_launch_market_activation (
      player_id text PRIMARY KEY,
      card_id text NOT NULL,
      is_new_card boolean NOT NULL,
      display_name text NOT NULL,
      sale_price numeric(18,4) NOT NULL,
      loan_fee numeric(18,4) NOT NULL,
      supply_batch_id text NOT NULL,
      history_id text NOT NULL,
      holding_id text NOT NULL,
      sale_listing_row_id text NOT NULL,
      sale_listing_public_id text NOT NULL,
      loan_listing_id text NOT NULL
    ) ON COMMIT DROP
  `);
  await client.query(
    `
      INSERT INTO tmp_launch_market_activation
      SELECT * FROM jsonb_to_recordset($1::jsonb) AS x(
        player_id text,
        card_id text,
        is_new_card boolean,
        display_name text,
        sale_price numeric,
        loan_fee numeric,
        supply_batch_id text,
        history_id text,
        holding_id text,
        sale_listing_row_id text,
        sale_listing_public_id text,
        loan_listing_id text
      )
    `,
    [JSON.stringify(rows)],
  );
  const cards = await client.query(
    `
      INSERT INTO player_cards (
        id, player_id, tier_id, edition_code, display_name, season_label,
        card_variant, supply_total, supply_available, is_active,
        metadata_json, created_at, updated_at
      )
      SELECT card_id, player_id, $1::text, $2::text, display_name, 'Launch 2026',
        'real_player', 5, 5, TRUE,
        '{"source":"launch_market_league_activation","realPlayer":true}',
        NOW(), NOW()
      FROM tmp_launch_market_activation
      WHERE is_new_card IS TRUE
      ON CONFLICT (player_id, tier_id, edition_code) DO NOTHING
    `,
    [tierId, LAUNCH_EDITION_CODE],
  );
  const batches = await client.query(
    `
      INSERT INTO player_card_supply_batches (
        id, batch_key, player_card_id, player_id, tier_id, quantity,
        status, source_type, source_reference, notes, metadata_json, created_at
      )
      SELECT supply_batch_id,
        'launch-market:' || player_id || ':' || $1::text || ':' || $2::text,
        card_id, player_id, $1::text, 5, 'applied',
        'launch_market_league_activation', $2::text,
        'Launch league batch market activation.',
        '{"target_supply":5}', NOW()
      FROM tmp_launch_market_activation
      WHERE is_new_card IS TRUE
      ON CONFLICT (batch_key) DO NOTHING
    `,
    [tierId, LAUNCH_EDITION_CODE],
  );
  const history = await client.query(`
    INSERT INTO player_card_histories (
      id, player_card_id, event_type, description, delta_supply,
      delta_available, metadata_json, created_at
    )
    SELECT history_id, card_id, 'launch_supply_added',
      'Launch league batch market supply activated.', 5, 5,
      '{"source":"launch_market_league_activation"}', NOW()
    FROM tmp_launch_market_activation
    WHERE is_new_card IS TRUE
  `);
  const holdings = await client.query(
    `
      INSERT INTO player_card_holdings (
        id, player_card_id, owner_user_id, quantity_total, quantity_reserved,
        last_acquired_at, metadata_json, created_at, updated_at
      )
      SELECT holding_id, card_id, $1::text, 5, 0, NOW(),
        '{"source":"launch_market_league_activation"}',
        NOW(), NOW()
      FROM tmp_launch_market_activation
      ON CONFLICT (player_card_id, owner_user_id) DO NOTHING
    `,
    [marketMakerUserId],
  );
  await client.query(
    `
      UPDATE player_card_holdings h
      SET quantity_total = h.quantity_total + GREATEST(0, 2 - (h.quantity_total - h.quantity_reserved)),
          updated_at = NOW(),
          metadata_json = ((COALESCE(h.metadata_json, '{}'::json)::jsonb ||
            '{"launchMarketTopup":true}'::jsonb)::json)
      FROM tmp_launch_market_activation t
      WHERE h.player_card_id = t.card_id
        AND h.owner_user_id = $1::text
        AND (h.quantity_total - h.quantity_reserved) < 2
    `,
    [marketMakerUserId],
  );
  const sales = await client.query(
    `
      WITH inserted AS (
        INSERT INTO player_card_listings (
          id, listing_id, player_card_id, seller_user_id, quantity,
          price_per_card_credits, status, is_negotiable,
          integrity_context_json, metadata_json, created_at, updated_at
        )
        SELECT sale_listing_row_id, sale_listing_public_id, card_id, $1::text, 1,
          sale_price, 'open', FALSE, '{}',
          '{"source":"launch_market_league_activation"}',
          NOW(), NOW()
        FROM tmp_launch_market_activation t
        WHERE NOT EXISTS (
          SELECT 1 FROM player_card_listings l
          WHERE l.player_card_id = t.card_id
            AND l.seller_user_id = $1::text
            AND l.status = 'open'
        )
        RETURNING player_card_id
      )
      UPDATE player_card_holdings h
      SET quantity_reserved = h.quantity_reserved + 1,
          updated_at = NOW()
      FROM inserted i
      WHERE h.player_card_id = i.player_card_id
        AND h.owner_user_id = $1::text
      RETURNING h.player_card_id
    `,
    [marketMakerUserId],
  );
  const loans = await client.query(
    `
      WITH inserted AS (
        INSERT INTO card_loan_listings (
          id, player_card_id, owner_user_id, total_slots, available_slots,
          duration_days, loan_fee_credits, currency, status, is_negotiable,
          expires_at, usage_restrictions_json, borrower_rights_json,
          lender_restrictions_json, terms_json, metadata_json, created_at, updated_at
        )
        SELECT loan_listing_id, card_id, $1::text, 1, 1, 7, loan_fee,
          'gtex_coin', 'open', TRUE, NOW() + INTERVAL '30 days',
          '{}', '{}', '{}',
          '{"source":"launch_market_league_activation"}',
          '{"source":"launch_market_league_activation"}',
          NOW(), NOW()
        FROM tmp_launch_market_activation t
        WHERE NOT EXISTS (
          SELECT 1 FROM card_loan_listings l
          WHERE l.player_card_id = t.card_id
            AND l.owner_user_id = $1::text
            AND l.status = 'open'
        )
        RETURNING player_card_id
      )
      UPDATE player_card_holdings h
      SET quantity_reserved = h.quantity_reserved + 1,
          updated_at = NOW()
      FROM inserted i
      WHERE h.player_card_id = i.player_card_id
        AND h.owner_user_id = $1::text
      RETURNING h.player_card_id
    `,
    [marketMakerUserId],
  );
  return {
    scopedPlayers: rows.length,
    newCards: cards.rowCount,
    supplyBatches: batches.rowCount,
    historyRows: history.rowCount,
    holdings: holdings.rowCount,
    saleListings: sales.rowCount,
    loanListings: loans.rowCount,
  };
}

async function summarize(client, leagueIds) {
  const result = await client.query(
    `
      SELECT
        p.league_id::text AS league_id,
        COUNT(DISTINCT ip.id)::int AS players,
        COUNT(DISTINCT pim.id)::int AS approved_images,
        COUNT(DISTINCT pc.id)::int AS cards,
        COUNT(DISTINCT pcl.id) FILTER (WHERE pcl.status = 'open')::int AS open_sales,
        COUNT(DISTINCT cll.id) FILTER (WHERE cll.status = 'open')::int AS open_loans
      FROM ingestion_players ip
      JOIN players p ON p.player_id::text = ip.provider_external_id
      LEFT JOIN ingestion_player_image_metadata pim
        ON pim.player_id = ip.id
       AND pim.image_role = 'portrait'
       AND pim.moderation_status = 'approved'
       AND pim.rights_cleared IS TRUE
       AND pim.source_url IS NOT NULL
      LEFT JOIN player_cards pc ON pc.player_id = ip.id AND pc.edition_code = $1
      LEFT JOIN player_card_listings pcl ON pcl.player_card_id = pc.id
      LEFT JOIN card_loan_listings cll ON cll.player_card_id = pc.id
      WHERE ip.source_provider = 'sportmonks'
        AND ip.is_real_player IS TRUE
        AND ip.is_tradable IS TRUE
        AND p.league_id = ANY($2::bigint[])
      GROUP BY p.league_id
      ORDER BY p.league_id
    `,
    [LAUNCH_EDITION_CODE, leagueIds],
  );
  return result.rows;
}

async function main() {
  const marketMakerUserId = process.env.LAUNCH_MARKET_MAKER_USER_ID || DEFAULT_MARKET_MAKER_USER_ID;
  const leagueIds = parseLeagueIds();
  const playerIds = parsePlayerIds();
  const dryRun = ["1", "true", "yes"].includes(
    String(process.env.LAUNCH_MARKET_DRY_RUN || "").toLowerCase(),
  );
  const pool = new Pool({
    connectionString: config.databaseUrl,
    ssl: config.databaseSsl ? { rejectUnauthorized: false } : false,
  });
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query("SET LOCAL statement_timeout = '10min'");
    const tierId = await ensureTier(client);
    const rows = await loadScopedPlayers(client, tierId, leagueIds, playerIds);
    const activation = dryRun
      ? {
          scopedPlayers: rows.length,
          newCards: rows.filter((row) => row.is_new_card).length,
          supplyBatches: 0,
          historyRows: 0,
          holdings: 0,
          saleListings: 0,
          loanListings: 0,
        }
      : await activateMarket(client, rows, tierId, marketMakerUserId);
    const byLeague = leagueIds.length ? await summarize(client, leagueIds) : [];
    if (dryRun) {
      await client.query("ROLLBACK");
    } else {
      await client.query("COMMIT");
    }
    process.stdout.write(
      `${JSON.stringify(
        {
          dryRun,
          leagueIds,
          playerIdScopeCount: playerIds.length,
          marketMakerUserId,
          activation,
          byLeague,
        },
        null,
        2,
      )}\n`,
    );
  } catch (error) {
    await client.query("ROLLBACK").catch(() => {});
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch((error) => {
  process.stderr.write(
    `${JSON.stringify({ event: "launch_market_activation_failed", reason: error.message })}\n`,
  );
  process.exitCode = 1;
});
