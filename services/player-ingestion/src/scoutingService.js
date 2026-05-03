"use strict";

const db = require("./db");
const { fitScore, scoutingSummary } = require("./scoutingNetwork");

async function createScoutingAssignment({
  teamId,
  managerId = null,
  region,
  minPotential = 75,
} = {}) {
  const result = await db.query(
    `
      INSERT INTO season_scouting_assignments (
        team_id,
        manager_id,
        region,
        min_potential,
        status,
        updated_at
      )
      VALUES ($1, $2, $3, $4, 'active', NOW())
      RETURNING *
    `,
    [teamId, managerId, region, minPotential],
  );
  return result.rows[0];
}

async function runScoutingAssignment(assignmentId) {
  const assignmentResult = await db.query(
    "SELECT * FROM season_scouting_assignments WHERE id = $1",
    [assignmentId],
  );
  const assignment = assignmentResult.rows[0];
  if (!assignment) {
    throw new Error(`Scouting assignment ${assignmentId} not found`);
  }
  const playersResult = await db.query(
    `
      SELECT *
      FROM players
      WHERE LOWER(COALESCE(nationality, '')) = LOWER($1)
        AND COALESCE(potential, 0) >= $2
        AND COALESCE(is_retired, FALSE) = FALSE
      ORDER BY COALESCE(potential, 0) DESC, COALESCE(age, 99) ASC
      LIMIT 50
    `,
    [assignment.region, assignment.min_potential],
  );
  const reports = [];
  for (const player of playersResult.rows) {
    const score = fitScore(player);
    const report = await db.query(
      `
        INSERT INTO season_scouting_reports (
          assignment_id,
          player_id,
          team_id,
          region,
          potential,
          fit_score,
          summary
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (assignment_id, player_id)
        DO UPDATE SET
          fit_score = EXCLUDED.fit_score,
          summary = EXCLUDED.summary
        RETURNING *
      `,
      [
        assignment.id,
        player.player_id,
        assignment.team_id,
        assignment.region,
        player.potential,
        score,
        scoutingSummary(player),
      ],
    );
    reports.push(report.rows[0]);
  }
  await db.query(
    `
      UPDATE season_scouting_assignments
      SET updated_at = NOW()
      WHERE id = $1
    `,
    [assignment.id],
  );
  return reports;
}

module.exports = {
  createScoutingAssignment,
  runScoutingAssignment,
};
