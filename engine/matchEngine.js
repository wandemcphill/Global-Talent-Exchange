const { createRNG } = require("./random");
const { decidePossession, generateAttackSequence } = require("./eventGenerator");

function simulateMatch(teamA, teamB, seed, options = {}) {
  const rng = createRNG(seed);
  const state = {
    score: { [teamA.id]: 0, [teamB.id]: 0 },
    lastScoringTeamId: "",
  };
  const timeline = [];
  const stepMinutes = options.stepMinutes || 5;

  timeline.push({
    minute: 0,
    type: "commentary",
    team: teamA.id,
    commentary: `${teamA.name} kick off against ${teamB.name}.`,
    overlay: "GTEX LIVE FEED",
  });

  for (let minute = 3; minute <= 90; minute += stepMinutes) {
    const possessionTeam = decidePossession(teamA, teamB, rng, state);
    const defendingTeam = possessionTeam.id === teamA.id ? teamB : teamA;
    if (!rng.chance(0.74)) {
      timeline.push({
        minute,
        type: "commentary",
        team: possessionTeam.id,
        commentary: `${possessionTeam.name} control the spell without a clear opening.`,
      });
      continue;
    }

    const sequence = generateAttackSequence(
      possessionTeam,
      defendingTeam,
      minute + rng.nextFloat() * 0.75,
      rng,
      state,
    );

    if (sequence.length === 0 && rng.chance(0.12)) {
      timeline.push({
        minute,
        type: "commentary",
        team: possessionTeam.id,
        commentary: `${possessionTeam.name} recycle possession without creating a clear opening.`,
      });
      continue;
    }

    for (const event of sequence) {
      timeline.push(event);
    }
  }

  timeline.push({
    minute: 90,
    type: "commentary",
    team: teamA.id,
    commentary: `Full time. ${teamA.name} ${state.score[teamA.id]}-${state.score[teamB.id]} ${teamB.name}.`,
    overlay: "FULL TIME",
  });

  timeline.sort((left, right) => left.minute - right.minute);

  return {
    matchId: `gtex-${seed}`,
    homeTeam: teamA.name,
    awayTeam: teamB.name,
    seed,
    score: {
      home: state.score[teamA.id],
      away: state.score[teamB.id],
    },
    events: timeline,
  };
}

module.exports = { simulateMatch };
