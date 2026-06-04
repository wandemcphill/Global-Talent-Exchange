function tacticModifier(tactic, category) {
  const table = {
    attacking: { attack: 1.15, risk: 1.12, control: 0.96, defend: 0.92 },
    balanced: { attack: 1.0, risk: 1.0, control: 1.0, defend: 1.0 },
    defensive: { attack: 0.9, risk: 0.88, control: 1.04, defend: 1.12 },
  };

  return table[tactic] && table[tactic][category] ? table[tactic][category] : 1;
}

function decidePossession(teamA, teamB, rng, state) {
  const teamAControl =
    teamA.average("passing") * 0.45 +
    teamA.average("positioning") * 0.35 +
    teamA.average("composure") * 0.2;
  const teamBControl =
    teamB.average("passing") * 0.45 +
    teamB.average("positioning") * 0.35 +
    teamB.average("composure") * 0.2;

  const total = Math.max(1, teamAControl + teamBControl);
  let teamAChance = teamAControl / total;

  if (state.lastScoringTeamId === teamA.id) {
    teamAChance -= 0.03;
  } else if (state.lastScoringTeamId === teamB.id) {
    teamAChance += 0.03;
  }

  teamAChance = Math.max(0.2, Math.min(0.8, teamAChance));
  return rng.chance(teamAChance) ? teamA : teamB;
}

function generateAttackSequence(teamInPossession, opponent, minute, rng, state) {
  const attackers = teamInPossession.outfieldPlayers;
  const defenders = opponent.outfieldPlayers;
  if (attackers.length < 3 || defenders.length < 2) {
    return [];
  }

  const buildUpCount = rng.nextInt(2, 3);
  const events = [];
  let timeCursor = minute;
  let current = selectCarrier(teamInPossession, rng);

  for (let index = 0; index < buildUpCount; index += 1) {
    const target = selectPassTarget(teamInPossession, current, rng);
    if (!target) {
      break;
    }

    const throughChance =
      0.18 *
      tacticModifier(teamInPossession.tactic, "risk") *
      ((target.positioning + current.passing) / 140);
    const type = rng.chance(throughChance) ? "through_pass" : "pass";
    events.push({
      minute: roundMinute(timeCursor),
      type,
      team: teamInPossession.id,
      from: current.id,
      to: target.id,
      commentary:
        type === "through_pass"
          ? `${current.name} slides a measured through ball for ${target.name}.`
          : `${current.name} finds ${target.name} with a short pass.`,
    });

    current = target;
    timeCursor += 0.35;
  }

  if (rng.chance(0.22 * tacticModifier(teamInPossession.tactic, "control"))) {
    events.push({
      minute: roundMinute(timeCursor),
      type: "dribble",
      team: teamInPossession.id,
      player: current.id,
      duration: 1.1,
      commentary: `${current.name} carries the move into the final third.`,
      x: teamInPossession.id === "home" ? rng.nextInt(12, 34) : rng.nextInt(-34, -12),
      z: rng.nextInt(-20, 20),
    });
    timeCursor += 0.45;
  }

  const defender = rng.pick(defenders);
  if (defender && rng.chance(0.18 * tacticModifier(opponent.tactic, "defend"))) {
    events.push({
      minute: roundMinute(timeCursor),
      type: "tackle",
      team: opponent.id,
      player: defender.id,
      target: current.id,
      commentary: `${defender.name} steps in to challenge ${current.name}.`,
    });
    timeCursor += 0.25;
  }

  const shotQuality = calculateShotQuality(current, teamInPossession, opponent);
  const shouldShoot =
    rng.chance(0.46 * tacticModifier(teamInPossession.tactic, "attack")) ||
    shotQuality > 0.61;
  if (!shouldShoot) {
    return events;
  }

  const outcome = resolveShotOutcome(current, opponent, shotQuality, rng);
  events.push({
    minute: roundMinute(timeCursor),
    type: "shot",
    team: teamInPossession.id,
    player: current.id,
    outcome,
    duration: 1.2,
    commentary: `${current.name} gets the shot away.`,
  });

  timeCursor += 0.25;
  if (outcome === "goal") {
    state.score[teamInPossession.id] += 1;
    state.lastScoringTeamId = teamInPossession.id;
    events.push({
      minute: roundMinute(timeCursor),
      type: "goal",
      team: teamInPossession.id,
      player: current.id,
      commentary: `Goal for ${teamInPossession.name}. ${current.name} finishes the move.`,
    });
  } else {
    events.push({
      minute: roundMinute(timeCursor),
      type: "save",
      team: opponent.id,
      player: opponent.goalkeeper ? opponent.goalkeeper.id : `${opponent.id}-1`,
      commentary: `${opponent.goalkeeper ? opponent.goalkeeper.name : "The keeper"} makes the save.`,
    });
  }

  return events;
}

function selectCarrier(team, rng) {
  const weighted = team.outfieldPlayers.filter((player) => player.role !== "DF");
  return rng.pick(weighted.length > 0 ? weighted : team.outfieldPlayers);
}

function selectPassTarget(team, current, rng) {
  const candidates = team.outfieldPlayers.filter((player) => player.id !== current.id);
  if (candidates.length === 0) {
    return null;
  }

  const sorted = candidates
    .slice()
    .sort(
      (left, right) =>
        right.positioning + right.passing * 0.4 - (left.positioning + left.passing * 0.4),
    );

  return rng.pick(sorted.slice(0, Math.min(5, sorted.length)));
}

function calculateShotQuality(shooter, attackingTeam, defendingTeam) {
  const shooting = shooter.shooting / 100;
  const composure = shooter.composure / 100;
  const support = attackingTeam.average("passing") / 100;
  const resistance = defendingTeam.average("tackling") / 100;
  return Math.max(0.05, Math.min(0.82, shooting * 0.38 + composure * 0.22 + support * 0.16 - resistance * 0.17));
}

function resolveShotOutcome(shooter, defendingTeam, shotQuality, rng) {
  const keeperStrength = defendingTeam.goalkeeper
    ? (defendingTeam.goalkeeper.positioning + defendingTeam.goalkeeper.composure) / 200
    : 0.55;
  const goalChance = shotQuality * 0.52 - keeperStrength * 0.2;
  return rng.chance(Math.max(0.05, Math.min(0.42, goalChance))) ? "goal" : "save";
}

function roundMinute(value) {
  return Math.round(value * 100) / 100;
}

module.exports = {
  decidePossession,
  generateAttackSequence,
};
