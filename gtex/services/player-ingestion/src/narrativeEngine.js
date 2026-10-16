"use strict";

function generateNarrative(match) {
  const narratives = [];
  if (match.isDerby) {
    narratives.push({
      type: "rivalry",
      description: "Fierce derby clash",
      impact: 0.1,
      teamId: null,
    });
  }

  if (match.upset) {
    narratives.push({
      type: "underdog",
      description: "Shocking upset win",
      impact: 0.15,
      teamId: match.winnerTeamId,
    });
  }

  if (match.heavyDefeatTeamId) {
    narratives.push({
      type: "pressure",
      description: "Manager pressure rises after a heavy defeat",
      impact: -0.08,
      teamId: match.heavyDefeatTeamId,
    });
  }

  if (match.lateWinnerTeamId) {
    narratives.push({
      type: "late_drama",
      description: "A late winner lifts the dressing room",
      impact: 0.08,
      teamId: match.lateWinnerTeamId,
    });
  }

  return narratives;
}

function applyNarrative(player, narrative) {
  const impact = normalizeImpact(narrative?.impact || 0);
  return {
    ...player,
    morale: clamp(Number(player.morale ?? 50) + impact, 0, 100),
  };
}

function deriveMatchNarratives({ fixture, result, home, away, events }) {
  const homeStrength = Number(home.team?.strength || 50);
  const awayStrength = Number(away.team?.strength || 50);
  const winnerTeamId =
    result.homeScore === result.awayScore
      ? null
      : result.homeScore > result.awayScore
        ? fixture.home_team
        : fixture.away_team;
  const loserTeamId =
    winnerTeamId === null
      ? null
      : Number(winnerTeamId) === Number(fixture.home_team)
        ? fixture.away_team
        : fixture.home_team;
  const winnerWasUnderdog =
    winnerTeamId &&
    ((Number(winnerTeamId) === Number(fixture.home_team) && homeStrength + 10 < awayStrength) ||
      (Number(winnerTeamId) === Number(fixture.away_team) && awayStrength + 10 < homeStrength));
  const goalDifference = Math.abs(result.homeScore - result.awayScore);
  const lateWinner = events.find(
    (event) =>
      event.type === "goal" && event.minute >= 85 && Number(event.teamId) === Number(winnerTeamId),
  );

  return generateNarrative({
    isDerby: isDerbyFixture(home.team, away.team),
    upset: Boolean(winnerWasUnderdog),
    winnerTeamId,
    heavyDefeatTeamId: goalDifference >= 3 ? loserTeamId : null,
    lateWinnerTeamId: lateWinner ? winnerTeamId : null,
  });
}

function narrativeMoraleDelta(narrative) {
  return normalizeImpact(narrative?.impact || 0);
}

function isDerbyFixture(homeTeam, awayTeam) {
  if (!homeTeam || !awayTeam) {
    return false;
  }
  if (
    homeTeam.league_id &&
    awayTeam.league_id &&
    Number(homeTeam.league_id) !== Number(awayTeam.league_id)
  ) {
    return false;
  }
  return Math.abs(Number(homeTeam.team_id || 0) - Number(awayTeam.team_id || 0)) <= 3;
}

function normalizeImpact(impact) {
  const number = Number(impact) || 0;
  return Math.abs(number) <= 1 ? number * 100 : number;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

module.exports = {
  applyNarrative,
  deriveMatchNarratives,
  generateNarrative,
  narrativeMoraleDelta,
};
