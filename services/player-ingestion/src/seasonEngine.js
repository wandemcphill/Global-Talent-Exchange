"use strict";

const config = require("./config");
const db = require("./db");
const { renderAudioCommentary } = require("./audioCommentary");
const { buildLiveMatchPayload, generateCommentary, scoreText } = require("./commentaryEngine");
const { attachPlayerNames, generateMatchEvents, getHighlights } = require("./highlightEvents");
const logger = require("./logger");
const {
  adjustTactics,
  chooseTactics,
  makeSubstitution,
  managerPressureDelta,
  pickLineup,
  tacticProfile,
} = require("./managerAI");
const { postMatchUpdate } = require("./matchInfluence");
const { deriveMatchNarratives, narrativeMoraleDelta } = require("./narrativeEngine");
const { evolveChemistry, initialChemistry, relationshipKey } = require("./relationships");
const repository = require("./repository");
const { simulateMatchSnapshot } = require("./simulation");
const { generateYouthForTeam } = require("./youthAcademy");

const DAY_MS = 24 * 60 * 60 * 1000;

function generateFixtures(teams) {
  const teamIds = teams.map((team) => Number(team.team_id || team.teamId || team)).filter(Boolean);
  const fixtures = [];
  for (let i = 0; i < teamIds.length; i += 1) {
    for (let j = i + 1; j < teamIds.length; j += 1) {
      fixtures.push({ homeTeam: teamIds[i], awayTeam: teamIds[j] });
      fixtures.push({ homeTeam: teamIds[j], awayTeam: teamIds[i] });
    }
  }
  return fixtures;
}

function assignDates(fixtures, startDate, fixturesPerDay = config.season.fixturesPerDay) {
  const start = normalizeDate(startDate);
  return fixtures.map((fixture, index) => ({
    ...fixture,
    matchDate: new Date(start.getTime() + Math.floor(index / fixturesPerDay) * DAY_MS),
  }));
}

function generateCupRound(teams, random = Math.random) {
  const shuffled = [...teams].sort(() => random() - 0.5);
  const fixtures = [];
  for (let index = 0; index < shuffled.length; index += 2) {
    if (shuffled[index + 1] === undefined) {
      continue;
    }
    fixtures.push({
      homeTeam: Number(shuffled[index].team_id || shuffled[index].teamId || shuffled[index]),
      awayTeam: Number(
        shuffled[index + 1].team_id || shuffled[index + 1].teamId || shuffled[index + 1],
      ),
    });
  }
  return fixtures;
}

function qualifyForContinental(leagueTable, slots = 4) {
  return sortTable(leagueTable).slice(0, slots);
}

function assignCompetitionDates(fixtures, startDate, type) {
  const start = nextCompetitionDate(normalizeDate(startDate), type);
  return fixtures.map((fixture, index) => ({
    ...fixture,
    matchDate: new Date(start.getTime() + index * 7 * DAY_MS),
  }));
}

async function createSeasonSchedule({
  name,
  startDate,
  endDate,
  leagueId = null,
  teamIds = null,
  fixturesPerDay = config.season.fixturesPerDay,
} = {}) {
  const teams = await resolveSeasonTeams({ leagueId, teamIds });
  if (teams.length < 2) {
    throw new Error("At least two teams are required to create a season schedule");
  }

  const datedFixtures = assignDates(generateFixtures(teams), startDate, fixturesPerDay);
  const resolvedEndDate =
    endDate || datedFixtures[datedFixtures.length - 1]?.matchDate || normalizeDate(startDate);

  return db.withTransaction(async (client) => {
    const seasonResult = await client.query(
      `
        INSERT INTO seasons (
          name,
          league_id,
          start_date,
          end_date,
          is_active,
          simulation_date,
          updated_at
        )
        VALUES ($1, $2, $3, $4, TRUE, $3, NOW())
        RETURNING *
      `,
      [name || defaultSeasonName(startDate), leagueId, normalizeDate(startDate), resolvedEndDate],
    );
    const season = seasonResult.rows[0];
    const competition = await insertCompetition(client, {
      seasonId: season.id,
      name: `${season.name} League`,
      type: "league",
      priority: 50,
    });

    for (const team of teams) {
      await insertCompetitionTeam(client, competition.id, team.team_id);
      await client.query(
        `
          INSERT INTO standings (team_id, season_id)
          VALUES ($1, $2)
          ON CONFLICT (team_id, season_id)
          DO NOTHING
        `,
        [team.team_id, season.id],
      );
    }

    for (const fixture of datedFixtures) {
      await client.query(
        `
          INSERT INTO fixtures (
            season_id,
            competition_id,
            home_team,
            away_team,
            match_date,
            fixture_type,
            priority
          )
          VALUES ($1, $2, $3, $4, $5, 'league', 50)
          ON CONFLICT DO NOTHING
        `,
        [season.id, competition.id, fixture.homeTeam, fixture.awayTeam, fixture.matchDate],
      );
    }

    logger.info("season schedule created", {
      event: "season_schedule_created",
      seasonId: season.id,
      leagueId,
      competitionId: competition.id,
      teamCount: teams.length,
      fixtureCount: datedFixtures.length,
    });

    return {
      season,
      competition,
      teamCount: teams.length,
      fixtureCount: datedFixtures.length,
    };
  });
}

async function createCompetitionSchedule({
  seasonId,
  name,
  type = "cup",
  teamIds,
  startDate,
  priority = type === "continental" ? 20 : type === "cup" ? 35 : 50,
  random = Math.random,
} = {}) {
  const teams = await resolveSeasonTeams({ teamIds });
  if (teams.length < 2) {
    throw new Error("At least two teams are required to create a competition schedule");
  }
  const rawFixtures = type === "league" ? generateFixtures(teams) : generateCupRound(teams, random);
  const datedFixtures =
    type === "league"
      ? assignDates(rawFixtures, startDate)
      : assignCompetitionDates(rawFixtures, startDate, type);

  return db.withTransaction(async (client) => {
    const competition = await insertCompetition(client, {
      seasonId,
      name,
      type,
      priority,
    });
    for (const [index, team] of teams.entries()) {
      await insertCompetitionTeam(client, competition.id, team.team_id, index + 1);
    }
    for (const [index, fixture] of datedFixtures.entries()) {
      await client.query(
        `
          INSERT INTO fixtures (
            season_id,
            competition_id,
            home_team,
            away_team,
            match_date,
            fixture_type,
            round_number,
            stage,
            priority
          )
          VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
          ON CONFLICT DO NOTHING
        `,
        [
          seasonId,
          competition.id,
          fixture.homeTeam,
          fixture.awayTeam,
          fixture.matchDate,
          type,
          type === "league" ? null : 1,
          type === "league" ? "league" : `round_${index + 1}`,
          priority,
        ],
      );
    }
    logger.info("competition schedule created", {
      event: "competition_schedule_created",
      competitionId: competition.id,
      seasonId,
      type,
      teamCount: teams.length,
      fixtureCount: datedFixtures.length,
    });
    return {
      competition,
      fixtureCount: datedFixtures.length,
      teamCount: teams.length,
    };
  });
}

async function runMatchday(date = new Date(), { random = Math.random } = {}) {
  const matchday = normalizeDate(date);
  const fixtures = await dueFixtures(matchday);
  const playingTeamIds = new Set();
  const results = [];

  for (const fixture of fixtures) {
    const result = await simulateAndSaveFixture(fixture, { random });
    results.push(result);
    playingTeamIds.add(Number(fixture.home_team));
    playingTeamIds.add(Number(fixture.away_team));
  }

  await recoverIdlePlayers([...playingTeamIds]);

  let transferCount = 0;
  if (config.season.transfersEnabled && isTransferWindow(matchday)) {
    transferCount = await runTransferWindowTick(matchday);
  }

  const endedSeasons = await completeFinishedSeasons(matchday);

  logger.info("season matchday completed", {
    event: "season_matchday_completed",
    date: toDateKey(matchday),
    fixtureCount: fixtures.length,
    transferCount,
    endedSeasons: endedSeasons.length,
  });

  return {
    date: matchday,
    fixtureCount: fixtures.length,
    results,
    transferCount,
    endedSeasons,
  };
}

async function simulateAndSaveFixture(fixture, { random = Math.random } = {}) {
  const [home, away] = await Promise.all([
    repository.getMatchTeamSnapshot(fixture.home_team),
    repository.getMatchTeamSnapshot(fixture.away_team),
  ]);
  const homeSelection = buildTeamPlan({
    label: "home",
    teamId: fixture.home_team,
    squad: home.players,
    manager: home.manager,
    opponentStrength: away.team.strength,
    scoreDelta: 0,
  });
  const awaySelection = buildTeamPlan({
    label: "away",
    teamId: fixture.away_team,
    squad: away.players,
    manager: away.manager,
    opponentStrength: home.team.strength,
    scoreDelta: 0,
  });
  const result = simulateMatchSnapshot(
    {
      players: homeSelection.starters,
      tactics: { ...(home.tactics || {}), ...homeSelection.tactics },
    },
    {
      players: awaySelection.starters,
      tactics: { ...(away.tactics || {}), ...awaySelection.tactics },
    },
    random,
  );
  const normalized = {
    homeScore: Math.max(0, Math.round(result.homeGoals || 0)),
    awayScore: Math.max(0, Math.round(result.awayGoals || 0)),
  };
  homeSelection.adaptation = buildAdaptation(
    home.manager,
    normalized.homeScore - normalized.awayScore,
  );
  awaySelection.adaptation = buildAdaptation(
    away.manager,
    normalized.awayScore - normalized.homeScore,
  );
  const playersById = mapPlayersById([...homeSelection.starters, ...awaySelection.starters]);
  const teamsById = new Map([
    [String(fixture.home_team), home.team],
    [String(fixture.away_team), away.team],
  ]);
  const rawEvents = generateMatchEvents({
    fixture,
    result: normalized,
    home: homeSelection,
    away: awaySelection,
    random,
  });
  const events = await enrichLiveEvents(
    attachPlayerNames(rawEvents, playersById, teamsById),
    normalized,
  );
  const narratives = deriveMatchNarratives({
    fixture,
    result: normalized,
    home,
    away,
    events,
  });

  await db.withTransaction(async (client) => {
    await client.query(
      `
        UPDATE fixtures
        SET played = TRUE,
            home_score = $2,
            away_score = $3,
            updated_at = NOW()
        WHERE id = $1
          AND played = FALSE
      `,
      [fixture.id, normalized.homeScore, normalized.awayScore],
    );
    await updateStandings(client, fixture, normalized);
    await persistMatchEvents(client, fixture, events);
    await persistNarratives(client, fixture, narratives);
    await applyPostMatchEffects(
      client,
      fixture,
      normalized,
      homeSelection.starters,
      awaySelection.starters,
      narratives,
      random,
    );
    await updateManagerPressure(client, fixture, normalized, home, away);
    await updateRelationships(client, homeSelection.starters, {
      won: normalized.homeScore > normalized.awayScore,
      lost: normalized.homeScore < normalized.awayScore,
    });
    await updateRelationships(client, awaySelection.starters, {
      won: normalized.awayScore > normalized.homeScore,
      lost: normalized.awayScore < normalized.homeScore,
    });
    await client.query(
      `
        UPDATE seasons
        SET simulation_date = GREATEST(COALESCE(simulation_date, $2), $2),
            last_tick_date = $2,
            updated_at = NOW()
        WHERE id = $1
      `,
      [fixture.season_id, normalizeDate(fixture.match_date)],
    );
  });

  await Promise.all([
    repository.recalculateTeamStrength(fixture.home_team),
    repository.recalculateTeamStrength(fixture.away_team),
  ]);

  logger.info("fixture simulated", {
    event: "fixture_simulated",
    fixtureId: fixture.id,
    seasonId: fixture.season_id,
    homeTeam: fixture.home_team,
    awayTeam: fixture.away_team,
    homeScore: normalized.homeScore,
    awayScore: normalized.awayScore,
    eventCount: events.length,
    highlightCount: getHighlights(events).length,
    narrativeCount: narratives.length,
  });

  return {
    fixtureId: fixture.id,
    ...normalized,
    events,
    highlights: getHighlights(events),
    narratives,
  };
}

async function updateStandings(client, fixture, result) {
  await ensureStandingRows(client, fixture);
  const homeOutcome = outcome(result.homeScore, result.awayScore);
  const awayOutcome = outcome(result.awayScore, result.homeScore);
  await applyStandingDelta(client, {
    seasonId: fixture.season_id,
    teamId: fixture.home_team,
    goalsFor: result.homeScore,
    goalsAgainst: result.awayScore,
    ...homeOutcome,
  });
  await applyStandingDelta(client, {
    seasonId: fixture.season_id,
    teamId: fixture.away_team,
    goalsFor: result.awayScore,
    goalsAgainst: result.homeScore,
    ...awayOutcome,
  });
}

async function applyPostMatchEffects(
  client,
  fixture,
  result,
  homePlayers,
  awayPlayers,
  narratives,
  random,
) {
  const homeWon = result.homeScore > result.awayScore;
  const awayWon = result.awayScore > result.homeScore;
  const moraleByTeam = narrativeMoraleByTeam(narratives);
  for (const player of homePlayers) {
    await updatePlayerAfterMatch(client, player, {
      goalsFor: result.homeScore,
      goalsAgainst: result.awayScore,
      won: homeWon,
      lost: awayWon,
      narrativeMorale: moraleByTeam.get(Number(fixture.home_team)) || moraleByTeam.get(0) || 0,
      random,
    });
  }
  for (const player of awayPlayers) {
    await updatePlayerAfterMatch(client, player, {
      goalsFor: result.awayScore,
      goalsAgainst: result.homeScore,
      won: awayWon,
      lost: homeWon,
      narrativeMorale: moraleByTeam.get(Number(fixture.away_team)) || moraleByTeam.get(0) || 0,
      random,
    });
  }
}

async function updatePlayerAfterMatch(client, player, context) {
  const rating = matchRating(player, context);
  const post = postMatchUpdate(player, rating);
  const fatiguedFitness = applyFatigue(player.fitness);
  const injury = injuryCheck({ ...player, fitness: fatiguedFitness }, context.random);
  const moralePenalty = fatiguedFitness < 30 ? 5 : 0;
  const morale = Math.max(0, Math.min(100, post.morale + (context.narrativeMorale || 0)));
  await client.query(
    `
      UPDATE players
      SET form = $2,
          morale = GREATEST(0, LEAST(100, $3 - $4)),
          fitness = $5,
          sharpness = LEAST(1, COALESCE(sharpness, 0.5) + 0.03),
          is_injured = $6,
          injury_return_date = $7,
          last_match_rating = $8,
          minutes_played = COALESCE(minutes_played, 0) + 90,
          updated_at = NOW()
      WHERE player_id = $1
    `,
    [
      player.player_id,
      post.form,
      morale,
      moralePenalty,
      fatiguedFitness,
      injury.isInjured,
      injury.injuryReturnDate,
      rating,
    ],
  );
}

async function enrichLiveEvents(events, result) {
  const match = {
    homeScore: result.homeScore,
    awayScore: result.awayScore,
  };
  const enriched = [];
  for (const event of events) {
    const commentary = generateCommentary(event, match);
    const audioUrl = await renderAudioCommentary(commentary, {
      event,
      match,
    });
    enriched.push({
      ...event,
      commentary,
      scoreText: scoreText(match),
      audioUrl,
      livePayload: buildLiveMatchPayload(
        {
          ...event,
          commentary,
          audioUrl,
        },
        match,
      ),
    });
  }
  return enriched;
}

function mapPlayersById(players) {
  return new Map(players.map((player) => [String(player.player_id || player.playerId), player]));
}

async function insertCompetition(client, { seasonId, name, type, priority }) {
  const result = await client.query(
    `
      INSERT INTO season_competitions (
        name,
        type,
        season_id,
        priority,
        updated_at
      )
      VALUES ($1, $2, $3, $4, NOW())
      RETURNING *
    `,
    [name, type, seasonId, priority],
  );
  return result.rows[0];
}

async function insertCompetitionTeam(client, competitionId, teamId, seed = null) {
  await client.query(
    `
      INSERT INTO season_competition_teams (
        competition_id,
        team_id,
        seed
      )
      VALUES ($1, $2, $3)
      ON CONFLICT (competition_id, team_id)
      DO NOTHING
    `,
    [competitionId, teamId, seed],
  );
}

function buildTeamPlan({ label, teamId, squad, manager, opponentStrength, scoreDelta }) {
  const selection = pickLineup(squad, manager);
  const decision = chooseTactics(manager, opponentStrength);
  const substitution = makeSubstitution({
    players: selection.starters,
    bench: selection.bench,
  });
  const adaptationDecision = adjustTactics(scoreDelta, 65, manager);
  return {
    label,
    teamId,
    manager,
    starters: selection.starters,
    bench: selection.bench,
    decision,
    tactics: tacticProfile(decision),
    substitution,
    adaptation: adaptationDecision
      ? {
          minute: 65,
          decision: adaptationDecision,
          tactics: tacticProfile(adaptationDecision),
        }
      : null,
  };
}

function buildAdaptation(manager, scoreDelta) {
  const minute = scoreDelta < 0 ? 64 : 78;
  const decision = adjustTactics(scoreDelta, minute, manager);
  return decision
    ? {
        minute,
        decision,
        tactics: tacticProfile(decision),
      }
    : null;
}

async function persistMatchEvents(client, fixture, events) {
  for (const event of events) {
    await client.query(
      `
        INSERT INTO season_match_events (
          fixture_id,
          minute,
          sequence,
          type,
          team_id,
          player_id,
          description,
          is_highlight,
          animation_key,
          commentary,
          score_text,
          audio_url,
          metadata_json
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::JSONB)
      `,
      [
        fixture.id,
        event.minute,
        event.sequence,
        event.type,
        event.teamId,
        event.playerId,
        event.description,
        event.isHighlight,
        event.animationKey,
        event.commentary || null,
        event.scoreText || null,
        event.audioUrl || null,
        JSON.stringify({
          ...(event.metadata || {}),
          live_payload: event.livePayload || null,
        }),
      ],
    );
  }
}

async function persistNarratives(client, fixture, narratives) {
  for (const narrative of narratives) {
    await client.query(
      `
        INSERT INTO season_narratives (
          fixture_id,
          competition_id,
          team_id,
          player_id,
          type,
          description,
          impact,
          metadata_json
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::JSONB)
      `,
      [
        fixture.id,
        fixture.competition_id || null,
        narrative.teamId || null,
        narrative.playerId || null,
        narrative.type,
        narrative.description,
        narrative.impact,
        JSON.stringify(narrative.metadata || {}),
      ],
    );
  }
}

async function updateManagerPressure(client, fixture, result, home, away) {
  const homeWon = result.homeScore > result.awayScore;
  const awayWon = result.awayScore > result.homeScore;
  const homeUpsetLoss =
    awayWon && Number(home.team.strength || 50) > Number(away.team.strength || 50) + 10;
  const awayUpsetLoss =
    homeWon && Number(away.team.strength || 50) > Number(home.team.strength || 50) + 10;
  await applyManagerPressure(client, fixture.home_team, {
    won: homeWon,
    lost: awayWon,
    upsetWin: homeWon && Number(home.team.strength || 50) + 10 < Number(away.team.strength || 50),
    upsetLoss: homeUpsetLoss,
  });
  await applyManagerPressure(client, fixture.away_team, {
    won: awayWon,
    lost: homeWon,
    upsetWin: awayWon && Number(away.team.strength || 50) + 10 < Number(home.team.strength || 50),
    upsetLoss: awayUpsetLoss,
  });
}

async function applyManagerPressure(client, teamId, result) {
  await client.query(
    `
      UPDATE season_managers
      SET pressure = GREATEST(0, LEAST(1, COALESCE(pressure, 0) + $2)),
          updated_at = NOW()
      WHERE team_id = $1
    `,
    [teamId, managerPressureDelta(result)],
  );
}

function narrativeMoraleByTeam(narratives) {
  const moraleByTeam = new Map();
  for (const narrative of narratives) {
    const teamId = narrative.teamId ? Number(narrative.teamId) : 0;
    moraleByTeam.set(teamId, (moraleByTeam.get(teamId) || 0) + narrativeMoraleDelta(narrative));
  }
  return moraleByTeam;
}

async function updateRelationships(client, players, outcome) {
  for (let i = 0; i < players.length; i += 1) {
    for (let j = i + 1; j < players.length; j += 1) {
      const [playerA, playerB] = relationshipKey(players[i], players[j]);
      if (!playerA || !playerB || playerA === playerB) {
        continue;
      }
      await client.query(
        `
          INSERT INTO season_player_relationships (
            player_a,
            player_b,
            chemistry,
            relationship_type,
            last_updated
          )
          VALUES ($1, $2, $3, 'teammate', NOW())
          ON CONFLICT (player_a, player_b)
          DO UPDATE SET
            chemistry = GREATEST(
              -1,
              LEAST(
                1,
                season_player_relationships.chemistry + $4
              )
            ),
            last_updated = NOW()
        `,
        [playerA, playerB, initialChemistry(players[i], players[j]), evolveChemistry(0, outcome)],
      );
    }
  }
}

function applyFatigue(fitness) {
  return Math.max(0, Number(fitness ?? 100) - 10);
}

function recoverFitness(fitness) {
  return Math.min(100, Number(fitness ?? 100) + 5);
}

function injuryCheck(player, random = Math.random) {
  const fitnessUnit = Math.max(0, Math.min(1, Number(player.fitness ?? 100) / 100));
  const risk = (1 - fitnessUnit) * 0.2;
  if (random() < risk) {
    const daysOut = 7 + Math.floor(random() * 22);
    return {
      isInjured: true,
      injuryReturnDate: new Date(Date.now() + daysOut * DAY_MS),
    };
  }
  return {
    isInjured: Boolean(player.is_injured),
    injuryReturnDate: player.injury_return_date || null,
  };
}

async function recoverIdlePlayers(playingTeamIds = []) {
  const params = playingTeamIds;
  const exclusionSql = params.length ? "AND NOT (team_id = ANY($1::BIGINT[]))" : "";
  await db.query(
    `
      UPDATE players
      SET fitness = LEAST(100, COALESCE(fitness, 100) + 5),
          is_injured = CASE
            WHEN injury_return_date IS NOT NULL AND injury_return_date <= NOW() THEN FALSE
            ELSE COALESCE(is_injured, FALSE)
          END,
          injury_return_date = CASE
            WHEN injury_return_date IS NOT NULL AND injury_return_date <= NOW() THEN NULL
            ELSE injury_return_date
          END,
          updated_at = NOW()
      WHERE COALESCE(is_retired, FALSE) = FALSE
        ${exclusionSql}
    `,
    params.length ? [params] : [],
  );
}

async function runTransferWindowTick(date = new Date()) {
  if (!isTransferWindow(date)) {
    return 0;
  }
  const candidates = await db.query(
    `
      WITH team_avg AS (
        SELECT team_id, AVG(COALESCE(overall, 50)) AS avg_overall
        FROM players
        WHERE team_id IS NOT NULL
          AND COALESCE(is_retired, FALSE) = FALSE
        GROUP BY team_id
      )
      SELECT p.player_id, p.team_id, p.overall
      FROM players p
      JOIN team_avg a ON a.team_id = p.team_id
      WHERE COALESCE(p.is_retired, FALSE) = FALSE
        AND COALESCE(p.is_injured, FALSE) = FALSE
        AND COALESCE(p.overall, 50) > COALESCE(a.avg_overall, 50) + 5
      ORDER BY COALESCE(p.overall, 50) DESC, p.player_id
      LIMIT $1
    `,
    [config.season.transferLimitPerTick],
  );
  let moved = 0;
  for (const player of candidates.rows) {
    const target = await weakestAlternativeTeam(player.team_id);
    if (!target) {
      continue;
    }
    await db.query(
      `
        UPDATE players
        SET team_id = $2,
            morale = GREATEST(0, COALESCE(morale, 50) - 10),
            updated_at = NOW()
        WHERE player_id = $1
      `,
      [player.player_id, target.team_id],
    );
    await repository.recordTransfer({
      playerId: player.player_id,
      fromTeam: player.team_id,
      toTeam: target.team_id,
      source: "season_window",
    });
    await Promise.all([
      repository.recalculateTeamStrength(player.team_id),
      repository.recalculateTeamStrength(target.team_id),
    ]);
    moved += 1;
  }
  return moved;
}

function isTransferWindow(date = new Date(), windows = config.season.transferWindows) {
  const current = normalizeDate(date).getTime();
  return windows.some((window) => {
    const start = normalizeDate(window.start).getTime();
    const end = normalizeDate(window.end).getTime();
    return current >= start && current <= end;
  });
}

async function endSeason(seasonId, { enqueueRegens = true } = {}) {
  const standings = await getStandings(seasonId);
  const seasonResult = await db.query("SELECT * FROM seasons WHERE id = $1", [seasonId]);
  const season = seasonResult.rows[0];
  if (!season) {
    throw new Error(`Season ${seasonId} not found`);
  }
  const teamIds = standings.map((row) => row.team_id);
  await retireOldPlayers(teamIds);
  await resetPlayerStates(teamIds);
  await db.query(
    `
      UPDATE seasons
      SET is_active = FALSE,
          updated_at = NOW()
      WHERE id = $1
    `,
    [seasonId],
  );
  let queuedRegens = 0;
  if (enqueueRegens && config.season.regenPerSeason > 0) {
    queuedRegens = await generateNewRegens(season, teamIds);
  }
  logger.info("season ended", {
    event: "season_ended",
    seasonId,
    queuedRegens,
  });
  return {
    seasonId,
    standings,
    queuedRegens,
  };
}

async function getStandings(seasonId) {
  const result = await db.query(
    `
      SELECT *,
             (goals_for - goals_against) AS goal_difference
      FROM standings
      WHERE season_id = $1
      ORDER BY points DESC,
               (goals_for - goals_against) DESC,
               goals_for DESC,
               wins DESC,
               team_id ASC
    `,
    [seasonId],
  );
  return result.rows;
}

function sortTable(teams) {
  return [...teams].sort((a, b) => {
    if (b.points !== a.points) {
      return b.points - a.points;
    }
    const bGoalDifference = b.goals_for - b.goals_against;
    const aGoalDifference = a.goals_for - a.goals_against;
    if (bGoalDifference !== aGoalDifference) {
      return bGoalDifference - aGoalDifference;
    }
    return b.goals_for - a.goals_for;
  });
}

async function completeFinishedSeasons(date = new Date()) {
  const result = await db.query(
    `
      SELECT s.id
      FROM seasons s
      WHERE s.is_active = TRUE
        AND NOT EXISTS (
          SELECT 1
          FROM fixtures f
          WHERE f.season_id = s.id
            AND f.played = FALSE
        )
        AND COALESCE(s.end_date, $1::DATE) <= $1::DATE
    `,
    [normalizeDate(date)],
  );
  const ended = [];
  for (const row of result.rows) {
    ended.push(await endSeason(row.id));
  }
  return ended;
}

async function resolveSeasonTeams({ leagueId = null, teamIds = null } = {}) {
  if (teamIds?.length) {
    const result = await db.query(
      `
        SELECT *
        FROM teams
        WHERE team_id = ANY($1::BIGINT[])
        ORDER BY team_id
      `,
      [teamIds.map((teamId) => Number(teamId))],
    );
    return result.rows;
  }
  const result = await db.query(
    `
      SELECT *
      FROM teams
      WHERE ($1::BIGINT IS NULL OR league_id = $1)
      ORDER BY team_id
    `,
    [leagueId],
  );
  return result.rows;
}

async function dueFixtures(date) {
  const result = await db.query(
    `
      SELECT f.*
      FROM fixtures f
      JOIN seasons s ON s.id = f.season_id
      WHERE f.played = FALSE
        AND s.is_active = TRUE
        AND f.match_date::DATE <= $1::DATE
      ORDER BY f.match_date ASC, COALESCE(f.priority, 50) ASC, f.id ASC
    `,
    [normalizeDate(date)],
  );
  return result.rows;
}

async function ensureStandingRows(client, fixture) {
  for (const teamId of [fixture.home_team, fixture.away_team]) {
    await client.query(
      `
        INSERT INTO standings (team_id, season_id)
        VALUES ($1, $2)
        ON CONFLICT (team_id, season_id)
        DO NOTHING
      `,
      [teamId, fixture.season_id],
    );
  }
}

async function applyStandingDelta(client, delta) {
  await client.query(
    `
      UPDATE standings
      SET played = played + 1,
          wins = wins + $3,
          draws = draws + $4,
          losses = losses + $5,
          goals_for = goals_for + $6,
          goals_against = goals_against + $7,
          points = points + $8,
          updated_at = NOW()
      WHERE season_id = $1
        AND team_id = $2
    `,
    [
      delta.seasonId,
      delta.teamId,
      delta.wins,
      delta.draws,
      delta.losses,
      delta.goalsFor,
      delta.goalsAgainst,
      delta.points,
    ],
  );
}

function outcome(goalsFor, goalsAgainst) {
  if (goalsFor > goalsAgainst) {
    return { wins: 1, draws: 0, losses: 0, points: 3 };
  }
  if (goalsFor < goalsAgainst) {
    return { wins: 0, draws: 0, losses: 1, points: 0 };
  }
  return { wins: 0, draws: 1, losses: 0, points: 1 };
}

function matchRating(player, { goalsFor, goalsAgainst, won, lost, random }) {
  const resultBias = won ? 0.6 : lost ? -0.4 : 0;
  const goalBias = Math.max(-0.6, Math.min(0.8, (goalsFor - goalsAgainst) * 0.15));
  const qualityBias = (Number(player.overall ?? 50) - 50) / 100;
  const noise = (random() - 0.5) * 0.8;
  return Math.max(3, Math.min(9.5, 6 + resultBias + goalBias + qualityBias + noise));
}

async function weakestAlternativeTeam(currentTeamId) {
  const result = await db.query(
    `
      SELECT team_id
      FROM teams
      WHERE team_id <> $1
      ORDER BY COALESCE(strength, 50) ASC, team_id ASC
      LIMIT 1
    `,
    [currentTeamId],
  );
  return result.rows[0] || null;
}

async function retireOldPlayers(teamIds) {
  if (!teamIds.length) {
    return;
  }
  await db.query(
    `
      UPDATE players
      SET is_retired = TRUE,
          retired_at = NOW(),
          updated_at = NOW()
      WHERE team_id = ANY($1::BIGINT[])
        AND COALESCE(age, 0) >= 37
        AND COALESCE(is_retired, FALSE) = FALSE
    `,
    [teamIds],
  );
}

async function resetPlayerStates(teamIds) {
  if (!teamIds.length) {
    return;
  }
  await db.query(
    `
      UPDATE players
      SET fitness = 100,
          morale = 50,
          form = 0.5,
          sharpness = 0.5,
          is_injured = FALSE,
          injury_return_date = NULL,
          updated_at = NOW()
      WHERE team_id = ANY($1::BIGINT[])
        AND COALESCE(is_retired, FALSE) = FALSE
    `,
    [teamIds],
  );
}

async function generateNewRegens(season, teamIds) {
  if (!teamIds.length) {
    return 0;
  }
  let queued = 0;
  const result = await db.query(
    `
      SELECT t.*, ya.nationality_bias, ya.yearly_intake, ya.identity
      FROM teams t
      LEFT JOIN season_youth_academies ya ON ya.team_id = t.team_id
      WHERE t.team_id = ANY($1::BIGINT[])
    `,
    [teamIds],
  );
  for (const team of result.rows) {
    const perTeamIntake = Math.max(
      1,
      Math.min(
        Number(team.yearly_intake || 3),
        Math.ceil(config.season.regenPerSeason / Math.max(result.rows.length, 1)),
      ),
    );
    queued += await generateYouthForTeam(
      {
        ...team,
        league_id: season.league_id || team.league_id,
      },
      {
        count: perTeamIntake,
        reason: "season_youth_pipeline",
      },
    );
    await db.query(
      `
        INSERT INTO season_youth_academies (
          team_id,
          nationality_bias,
          identity,
          yearly_intake,
          last_generated_at,
          updated_at
        )
        VALUES ($1, $2, COALESCE($3, 'balanced'), $4, NOW(), NOW())
        ON CONFLICT (team_id)
        DO UPDATE SET
          last_generated_at = NOW(),
          updated_at = NOW()
      `,
      [team.team_id, team.nationality_bias || null, team.identity || null, perTeamIntake],
    );
  }
  return queued;
}

function defaultSeasonName(startDate) {
  const date = normalizeDate(startDate);
  return `GTEX Season ${date.getUTCFullYear()}`;
}

function nextCompetitionDate(startDate, type) {
  const targetDay = type === "league" ? 6 : type === "continental" ? 2 : 3;
  const date = normalizeDate(startDate);
  while (date.getUTCDay() !== targetDay) {
    date.setUTCDate(date.getUTCDate() + 1);
  }
  return date;
}

function normalizeDate(value) {
  if (value instanceof Date) {
    return new Date(Date.UTC(value.getUTCFullYear(), value.getUTCMonth(), value.getUTCDate()));
  }
  const date = new Date(value || Date.now());
  if (Number.isNaN(date.getTime())) {
    throw new Error(`Invalid date: ${value}`);
  }
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}

function toDateKey(value) {
  return normalizeDate(value).toISOString().slice(0, 10);
}

module.exports = {
  applyFatigue,
  assignDates,
  assignCompetitionDates,
  createCompetitionSchedule,
  createSeasonSchedule,
  endSeason,
  generateCupRound,
  generateFixtures,
  getStandings,
  injuryCheck,
  isTransferWindow,
  qualifyForContinental,
  recoverFitness,
  runMatchday,
  runTransferWindowTick,
  sortTable,
};
