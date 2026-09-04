"use strict";

const { randomUUID } = require("node:crypto");
const db = require("./db");
const { defaultManagerForTeam } = require("./managerAI");

async function getSyncState(key) {
  const result = await db.query("SELECT last_synced FROM sync_state WHERE key = $1", [key]);
  return result.rows[0]?.last_synced || null;
}

async function setSyncState(key, timestamp = new Date()) {
  await db.query(
    `
      INSERT INTO sync_state (key, last_synced)
      VALUES ($1, $2)
      ON CONFLICT (key)
      DO UPDATE SET last_synced = EXCLUDED.last_synced
    `,
    [key, timestamp],
  );
}

async function getPlayer(playerId) {
  const result = await db.query("SELECT * FROM players WHERE player_id = $1", [playerId]);
  return result.rows[0] || null;
}

async function upsertPlayer(player) {
  const result = await db.query(
    `
      INSERT INTO players (
        player_id,
        name,
        nationality,
        age,
        image_url,
        is_regen,
        rights_cleared,
        updated_at,
        source_hash,
        source_provider,
        league_id,
        team_id,
        image_source,
        position,
        overall,
        potential,
        pace,
        shooting,
        passing,
        dribbling,
        defending,
        physical,
        morale,
        fitness,
        traits,
        personality,
        form,
        sharpness,
        is_injured,
        injury_return_date,
        minutes_played,
        last_match_rating
      )
      VALUES (
        $1, $2, $3, $4, $5, $6, $7, NOW(), $8, $9, $10, $11, $12,
        $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26,
        $27, $28, $29, $30, $31
      )
      ON CONFLICT (player_id)
      DO UPDATE SET
        name = EXCLUDED.name,
        nationality = EXCLUDED.nationality,
        age = EXCLUDED.age,
        image_url = EXCLUDED.image_url,
        is_regen = EXCLUDED.is_regen,
        rights_cleared = EXCLUDED.rights_cleared,
        updated_at = NOW(),
        source_hash = EXCLUDED.source_hash,
        source_provider = EXCLUDED.source_provider,
        league_id = EXCLUDED.league_id,
        team_id = EXCLUDED.team_id,
        image_source = EXCLUDED.image_source,
        position = EXCLUDED.position,
        overall = EXCLUDED.overall,
        potential = EXCLUDED.potential,
        pace = EXCLUDED.pace,
        shooting = EXCLUDED.shooting,
        passing = EXCLUDED.passing,
        dribbling = EXCLUDED.dribbling,
        defending = EXCLUDED.defending,
        physical = EXCLUDED.physical,
        morale = EXCLUDED.morale,
        fitness = EXCLUDED.fitness,
        traits = EXCLUDED.traits,
        personality = EXCLUDED.personality,
        form = EXCLUDED.form,
        sharpness = EXCLUDED.sharpness,
        is_injured = EXCLUDED.is_injured,
        injury_return_date = EXCLUDED.injury_return_date,
        minutes_played = EXCLUDED.minutes_played,
        last_match_rating = EXCLUDED.last_match_rating
      WHERE
        players.name IS DISTINCT FROM EXCLUDED.name
        OR players.nationality IS DISTINCT FROM EXCLUDED.nationality
        OR players.age IS DISTINCT FROM EXCLUDED.age
        OR players.image_url IS DISTINCT FROM EXCLUDED.image_url
        OR players.is_regen IS DISTINCT FROM EXCLUDED.is_regen
        OR players.rights_cleared IS DISTINCT FROM EXCLUDED.rights_cleared
        OR players.source_hash IS DISTINCT FROM EXCLUDED.source_hash
        OR players.source_provider IS DISTINCT FROM EXCLUDED.source_provider
        OR players.league_id IS DISTINCT FROM EXCLUDED.league_id
        OR players.team_id IS DISTINCT FROM EXCLUDED.team_id
        OR players.image_source IS DISTINCT FROM EXCLUDED.image_source
        OR players.position IS DISTINCT FROM EXCLUDED.position
        OR players.overall IS DISTINCT FROM EXCLUDED.overall
        OR players.potential IS DISTINCT FROM EXCLUDED.potential
        OR players.pace IS DISTINCT FROM EXCLUDED.pace
        OR players.shooting IS DISTINCT FROM EXCLUDED.shooting
        OR players.passing IS DISTINCT FROM EXCLUDED.passing
        OR players.dribbling IS DISTINCT FROM EXCLUDED.dribbling
        OR players.defending IS DISTINCT FROM EXCLUDED.defending
        OR players.physical IS DISTINCT FROM EXCLUDED.physical
        OR players.morale IS DISTINCT FROM EXCLUDED.morale
        OR players.fitness IS DISTINCT FROM EXCLUDED.fitness
        OR players.traits IS DISTINCT FROM EXCLUDED.traits
        OR players.personality IS DISTINCT FROM EXCLUDED.personality
        OR players.form IS DISTINCT FROM EXCLUDED.form
        OR players.sharpness IS DISTINCT FROM EXCLUDED.sharpness
        OR players.is_injured IS DISTINCT FROM EXCLUDED.is_injured
        OR players.injury_return_date IS DISTINCT FROM EXCLUDED.injury_return_date
        OR players.minutes_played IS DISTINCT FROM EXCLUDED.minutes_played
        OR players.last_match_rating IS DISTINCT FROM EXCLUDED.last_match_rating
      RETURNING player_id
    `,
    [
      player.playerId,
      player.name,
      player.nationality,
      player.age,
      player.imageUrl,
      player.isRegen,
      player.rightsCleared,
      player.sourceHash,
      player.sourceProvider,
      player.leagueId,
      player.teamId,
      player.imageSource,
      player.position,
      player.overall,
      player.potential,
      player.pace,
      player.shooting,
      player.passing,
      player.dribbling,
      player.defending,
      player.physical,
      player.morale,
      player.fitness,
      player.traits || [],
      player.personality,
      player.form ?? 0.5,
      player.sharpness ?? 0.5,
      player.isInjured ?? false,
      player.injuryReturnDate || null,
      player.minutesPlayed ?? 0,
      player.lastMatchRating ?? 0,
    ],
  );
  return result.rowCount > 0;
}

// The app reads share-market eligibility off ingestion_players.country_id /
// current_club_id (no free-text fallback for country) plus a handful of
// free-text club/league fields. This mirror wrote none of them: `player`
// already carries `nationality` and `teamId` by the time it gets here, but
// nothing resolved either into a reference, so every player this pipeline
// touched got permanently null country_id and current_club_id. That is the
// entire reason ~38% of tradable real players could never be issued a share
// market -- not a share-market bug, an ingestion mapping gap.
async function resolveCountryIdByName(nationality) {
  if (!nationality) {
    return null;
  }
  const result = await db.query(
    `
      SELECT id FROM ingestion_countries
      WHERE lower(name) = lower($1)
         OR lower(alpha2_code) = lower($1)
         OR lower(alpha3_code) = lower($1)
         OR lower(fifa_code) = lower($1)
      LIMIT 1
    `,
    [nationality],
  );
  return result.rows[0]?.id || null;
}

async function resolveClubIdBySportmonksTeamId(teamId) {
  if (!teamId) {
    return null;
  }
  const result = await db.query(
    `
      SELECT id FROM ingestion_clubs
      WHERE source_provider = 'sportmonks' AND provider_external_id = $1
      LIMIT 1
    `,
    [String(teamId)],
  );
  return result.rows[0]?.id || null;
}

async function upsertAppPlayerMirror(player) {
  if (!player?.playerId || !player?.name) {
    return null;
  }
  const [countryId, clubId] = await Promise.all([
    resolveCountryIdByName(player.nationality),
    resolveClubIdBySportmonksTeamId(player.teamId),
  ]);
  // The team is not always in ingestion_clubs yet (smaller leagues lag club
  // ingestion), so real_world_club_name carries the team name as a fallback
  // eligibility signal even when the FK does not resolve.
  const realWorldClubName = player.teamName || null;
  const result = await db.query(
    `
      INSERT INTO ingestion_players (
        id,
        source_provider,
        provider_external_id,
        full_name,
        short_name,
        position,
        normalized_position,
        last_synced_at,
        is_tradable,
        is_real_player,
        canonical_display_name,
        country_id,
        current_club_id,
        real_world_club_name,
        source_last_refreshed_at,
        dna_profile,
        morale,
        created_at,
        updated_at
      )
      VALUES (
        $1, $2, $3, $4, $5, $6, $7, NOW(), TRUE, $8, $9, $10, $11, $12, NOW(), $13, $14, NOW(), NOW()
      )
      ON CONFLICT (source_provider, provider_external_id)
      DO UPDATE SET
        full_name = COALESCE(EXCLUDED.full_name, ingestion_players.full_name),
        short_name = COALESCE(EXCLUDED.short_name, ingestion_players.short_name),
        position = COALESCE(EXCLUDED.position, ingestion_players.position),
        normalized_position = COALESCE(EXCLUDED.normalized_position, ingestion_players.normalized_position),
        last_synced_at = NOW(),
        is_tradable = TRUE,
        is_real_player = EXCLUDED.is_real_player,
        canonical_display_name = COALESCE(EXCLUDED.canonical_display_name, ingestion_players.canonical_display_name),
        country_id = COALESCE(ingestion_players.country_id, EXCLUDED.country_id),
        current_club_id = COALESCE(ingestion_players.current_club_id, EXCLUDED.current_club_id),
        real_world_club_name = COALESCE(ingestion_players.real_world_club_name, EXCLUDED.real_world_club_name),
        source_last_refreshed_at = NOW(),
        dna_profile = CASE
          WHEN ingestion_players.dna_profile IS NULL OR ingestion_players.dna_profile::text = '{}'::text
            THEN EXCLUDED.dna_profile
          ELSE ingestion_players.dna_profile
        END,
        morale = COALESCE(ingestion_players.morale, EXCLUDED.morale, 0.5),
        updated_at = NOW()
      RETURNING id
    `,
    [
      randomUUID(),
      player.sourceProvider || "sportmonks",
      String(player.playerId),
      player.name,
      player.name,
      player.position || null,
      player.position || null,
      !player.isRegen,
      player.name,
      countryId,
      clubId,
      realWorldClubName,
      JSON.stringify({
        source: "sportmonks_live_ingestion",
        overall: player.overall ?? null,
        potential: player.potential ?? null,
        pace: player.pace ?? null,
        shooting: player.shooting ?? null,
        passing: player.passing ?? null,
        dribbling: player.dribbling ?? null,
        defending: player.defending ?? null,
        physical: player.physical ?? null,
      }),
      player.morale ?? 0.5,
    ],
  );
  return result.rows[0]?.id || null;
}

async function upsertAppPlayerImageMetadata({
  appPlayerId,
  playerId,
  imageUrl,
  storageKey,
  rightsCleared,
}) {
  if (!appPlayerId || !playerId || !imageUrl || !rightsCleared) {
    return false;
  }
  const result = await db.query(
    `
      INSERT INTO ingestion_player_image_metadata (
        id,
        source_provider,
        provider_external_id,
        player_id,
        image_role,
        source_url,
        storage_key,
        mime_type,
        moderation_status,
        rights_cleared,
        is_primary,
        last_processed_at,
        created_at,
        updated_at
      )
      VALUES (
        $1, 'sportmonks', $2, $3, 'portrait', $4, $5, NULL, 'approved', TRUE, TRUE, NOW(), NOW(), NOW()
      )
      ON CONFLICT (player_id, image_role)
      DO UPDATE SET
        source_provider = EXCLUDED.source_provider,
        provider_external_id = EXCLUDED.provider_external_id,
        source_url = EXCLUDED.source_url,
        storage_key = EXCLUDED.storage_key,
        moderation_status = 'approved',
        rights_cleared = TRUE,
        is_primary = TRUE,
        last_processed_at = NOW(),
        updated_at = NOW()
      RETURNING id
    `,
    [
      randomUUID(),
      `sportmonks:player:${playerId}:portrait`,
      appPlayerId,
      imageUrl,
      storageKey || null,
    ],
  );
  return result.rowCount > 0;
}

async function upsertTeam(team) {
  if (!team?.teamId) {
    return;
  }
  await db.query(
    `
      INSERT INTO teams (
        team_id,
        name,
        league_id,
        strength,
        updated_at
      )
      VALUES ($1, $2, $3, COALESCE($4, 50), NOW())
      ON CONFLICT (team_id)
      DO UPDATE SET
        name = COALESCE(EXCLUDED.name, teams.name),
        league_id = COALESCE(EXCLUDED.league_id, teams.league_id),
        strength = COALESCE(teams.strength, EXCLUDED.strength, 50),
        updated_at = NOW()
    `,
    [team.teamId, team.name || null, team.leagueId || null, team.strength || null],
  );
}

async function recordTransfer({ playerId, fromTeam, toTeam, source = "sportmonks" }) {
  if (!playerId || !fromTeam || !toTeam || Number(fromTeam) === Number(toTeam)) {
    return;
  }
  await db.query(
    `
      INSERT INTO transfers (
        player_id,
        from_team,
        to_team,
        fee,
        date,
        source
      )
      VALUES ($1, $2, $3, 0, NOW(), $4)
    `,
    [playerId, fromTeam, toTeam, source],
  );
}

async function recalculateTeamStrength(teamId) {
  if (!teamId) {
    return null;
  }
  const result = await db.query(
    `
      WITH team_strength AS (
        SELECT
          COALESCE(
            AVG(COALESCE(overall, 50) * COALESCE(form, 0.5))
              FILTER (WHERE COALESCE(is_injured, FALSE) = FALSE),
            AVG(COALESCE(overall, 50) * COALESCE(form, 0.5)),
            50
          ) AS strength
        FROM players
        WHERE team_id = $1
      )
      INSERT INTO teams (
        team_id,
        strength,
        updated_at
      )
      SELECT $1, strength, NOW()
      FROM team_strength
      ON CONFLICT (team_id)
      DO UPDATE SET
        strength = EXCLUDED.strength,
        updated_at = NOW()
      RETURNING strength
    `,
    [teamId],
  );
  return result.rows[0]?.strength ?? null;
}

async function getMatchPlayerSnapshot(teamId) {
  const result = await db.query(
    `
      SELECT *
      FROM players
      WHERE team_id = $1
        AND COALESCE(is_injured, FALSE) = FALSE
        AND COALESCE(is_retired, FALSE) = FALSE
      ORDER BY COALESCE(overall, 50) DESC, COALESCE(form, 0.5) DESC
    `,
    [teamId],
  );
  return result.rows;
}

async function getMatchTeamSnapshot(teamId) {
  const [teamResult, tacticsResult, managerResult, players] = await Promise.all([
    db.query("SELECT * FROM teams WHERE team_id = $1", [teamId]),
    db.query("SELECT * FROM tactics WHERE team_id = $1", [teamId]),
    db.query("SELECT * FROM season_managers WHERE team_id = $1", [teamId]),
    getMatchPlayerSnapshot(teamId),
  ]);
  const team = teamResult.rows[0] || { team_id: teamId, strength: 50 };
  const manager = managerResult.rows[0] || defaultManagerForTeam(team);
  return {
    team,
    tactics: tacticsResult.rows[0] || null,
    manager,
    players,
  };
}

async function upsertDefaultManager(team) {
  const manager = defaultManagerForTeam(team);
  await db.query(
    `
      INSERT INTO season_managers (
        team_id,
        name,
        mentality,
        adaptability,
        risk,
        updated_at
      )
      VALUES ($1, $2, $3, $4, $5, NOW())
      ON CONFLICT (team_id)
      DO NOTHING
    `,
    [manager.teamId, manager.name, manager.mentality, manager.adaptability, manager.risk],
  );
  return manager;
}

async function upsertDefaultTactics(teamId) {
  const seed = Number(BigInt(teamId) % 4n);
  const profiles = [
    { formation: "4-3-3", style: "possession", pressing: 62, tempo: 58, width: 66, lineHeight: 61 },
    { formation: "4-2-3-1", style: "counter", pressing: 58, tempo: 68, width: 55, lineHeight: 49 },
    { formation: "4-4-2", style: "direct", pressing: 54, tempo: 64, width: 60, lineHeight: 53 },
    { formation: "5-3-2", style: "balanced", pressing: 52, tempo: 52, width: 48, lineHeight: 45 },
  ];
  const profile = profiles[seed];
  await db.query(
    `
      INSERT INTO tactics (
        team_id,
        formation,
        style,
        pressing,
        tempo,
        width,
        line_height,
        updated_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
      ON CONFLICT (team_id)
      DO NOTHING
    `,
    [
      teamId,
      profile.formation,
      profile.style,
      profile.pressing,
      profile.tempo,
      profile.width,
      profile.lineHeight,
    ],
  );
}

module.exports = {
  getPlayer,
  getMatchPlayerSnapshot,
  getMatchTeamSnapshot,
  getSyncState,
  recalculateTeamStrength,
  recordTransfer,
  setSyncState,
  upsertTeam,
  upsertDefaultTactics,
  upsertDefaultManager,
  upsertAppPlayerImageMetadata,
  upsertAppPlayerMirror,
  resolveCountryIdByName,
  resolveClubIdBySportmonksTeamId,
  upsertPlayer,
};
