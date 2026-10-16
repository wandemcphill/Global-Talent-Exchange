"use strict";

const { randomUUID } = require("node:crypto");
const db = require("./db");
const logger = require("./logger");

const DEFAULT_FREE_PLAYER_DISTRIBUTION = { high: 1, mid: 2, low: 2 };

const DEFINITIONS = [
  ["gtex-world-cup", "GTEX World Cup", "world_cup", "senior", "global"],
  ["gtex-u20-world-cup", "U20 World Cup", "world_cup", "u20", "global"],
  ["gtex-u17-world-cup", "U17 World Cup", "world_cup", "u17", "global"],
  ["gtex-afcon", "GTEX AFCON", "afcon", "senior", "afcon"],
  ["gtex-u20-afcon", "U20 AFCON", "afcon", "u20", "afcon"],
  ["gtex-u17-afcon", "U17 AFCON", "afcon", "u17", "afcon"],
  ["gtex-copa", "GTEX Copa", "copa", "senior", "copa"],
  ["gtex-u20-copa", "U20 Copa", "copa", "u20", "copa"],
  ["gtex-u17-copa", "U17 Copa", "copa", "u17", "copa"],
  ["gtex-euros", "GTEX Euros", "euros", "senior", "euros"],
  ["gtex-u20-euros", "U20 Euros", "euros", "u20", "euros"],
  ["gtex-u17-euros", "U17 Euros", "euros", "u17", "euros"],
];

function competitionEngineProfile(family, ageBand) {
  const worldSlots = ageBand === "u20" ? 24 : 48;
  const regionalSlots = ageBand === "u17" ? 16 : ageBand === "u20" ? 16 : 24;
  const regionalConfederations = {
    afcon: ["CAF"],
    copa: ["CONMEBOL"],
    euros: ["UEFA"],
  };
  return {
    family,
    age_band: ageBand,
    tournament_slots: family === "world_cup" ? worldSlots : regionalSlots,
    group_size: 4,
    advance_per_group: 2,
    best_third_slots: family === "world_cup" || ageBand === "senior" ? 4 : 0,
    qualifier_group_size: family === "copa" ? 5 : 4,
    eligible_confederations: regionalConfederations[family] || [],
    preferred_cycle_week: ageBand === "u17" ? 1 : ageBand === "u20" ? 3 : 2,
    schedule_label: `${ageBand.toUpperCase()} ${family.replaceAll("_", " ")} registration open`,
  };
}

async function findAdminUserId() {
  const result = await db.query(
    `
      SELECT id
      FROM users
      WHERE lower(role) IN ('super_admin', 'admin')
      ORDER BY CASE WHEN lower(role) = 'super_admin' THEN 0 ELSE 1 END, created_at ASC
      LIMIT 1
    `,
  );
  return result.rows[0]?.id || null;
}

async function seedNationalCompetitions() {
  const adminUserId = await findAdminUserId();
  const seasonLabel = String(new Date().getUTCFullYear());
  const entryOpensAt = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const entryClosesAt = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000);
  const kickoffAt = new Date(Date.now() + 97 * 24 * 60 * 60 * 1000);
  const summary = { created: 0, updated: 0, total: DEFINITIONS.length };

  for (const [key, title, family, ageBand, regionType] of DEFINITIONS) {
    const metadata = {
      competition_family: family,
      entry_mode: "rental_only",
      minimum_squad_size: 18,
      maximum_squad_size: 30,
      free_player_quota: 5,
      free_player_distribution: DEFAULT_FREE_PLAYER_DISTRIBUTION,
      competition_engine: competitionEngineProfile(family, ageBand),
      schedule_profile: {
        preferred_cycle_week: competitionEngineProfile(family, ageBand).preferred_cycle_week,
        label: competitionEngineProfile(family, ageBand).schedule_label,
      },
      launch_seeded: true,
    };
    const result = await db.query(
      `
        INSERT INTO national_team_competitions (
          id,
          key,
          title,
          season_label,
          region_type,
          age_band,
          format_type,
          status,
          notes,
          active,
          entry_opens_at,
          entry_closes_at,
          kickoff_at,
          metadata_json,
          created_by_user_id,
          created_at,
          updated_at
        )
        VALUES (
          $1, $2, $3, $4, $5, $6, 'cup', 'open',
          'Launch national-team rental competition seeded for managers.',
          TRUE, $7, $8, $9, $10, $11, NOW(), NOW()
        )
        ON CONFLICT (key)
        DO UPDATE SET
          status = CASE
            WHEN national_team_competitions.status IN ('locked', 'live', 'completed') THEN national_team_competitions.status
            ELSE 'open'
          END,
          active = TRUE,
          entry_opens_at = COALESCE(national_team_competitions.entry_opens_at, EXCLUDED.entry_opens_at),
          entry_closes_at = CASE
            WHEN national_team_competitions.completed_at IS NULL THEN GREATEST(
              COALESCE(national_team_competitions.entry_closes_at, EXCLUDED.entry_closes_at),
              EXCLUDED.entry_closes_at
            )
            ELSE national_team_competitions.entry_closes_at
          END,
          kickoff_at = CASE
            WHEN national_team_competitions.completed_at IS NULL THEN GREATEST(
              COALESCE(national_team_competitions.kickoff_at, EXCLUDED.kickoff_at),
              EXCLUDED.kickoff_at
            )
            ELSE national_team_competitions.kickoff_at
          END,
          metadata_json = (
            COALESCE(national_team_competitions.metadata_json, '{}'::json)::jsonb
            || EXCLUDED.metadata_json::jsonb
          )::json,
          updated_at = NOW()
        RETURNING (xmax = 0) AS inserted
      `,
      [
        randomUUID(),
        key,
        title,
        seasonLabel,
        regionType,
        ageBand,
        entryOpensAt,
        entryClosesAt,
        kickoffAt,
        JSON.stringify(metadata),
        adminUserId,
      ],
    );
    if (result.rows[0]?.inserted) {
      summary.created += 1;
    } else {
      summary.updated += 1;
    }
  }

  logger.info("national competitions seeded", {
    event: "national_competitions_seeded",
    ...summary,
  });
  return summary;
}

if (require.main === module) {
  seedNationalCompetitions()
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
  seedNationalCompetitions,
};
