"use strict";

const HIGHLIGHT_TYPES = new Set(["goal", "red_card", "big_chance"]);

function recordEvent(matchId, minute, type, player, extra = {}) {
  return {
    matchId,
    minute,
    type,
    playerId: player?.player_id || player?.playerId || player?.id || null,
    teamId: extra.teamId || player?.team_id || player?.teamId || null,
    description: extra.description || `${player?.name || "Player"} ${type.replace(/_/g, " ")}`,
    isHighlight: HIGHLIGHT_TYPES.has(type),
    animationKey: mapEventToAnimation(type),
    metadata: extra.metadata || {},
  };
}

function generateMatchEvents({ fixture, result, home, away, random = Math.random }) {
  const events = [];
  let sequence = 1;
  const add = (event) => {
    events.push({
      ...event,
      sequence,
    });
    sequence += 1;
  };

  addGoalEvents({
    count: result.homeScore,
    fixture,
    lineup: home.starters,
    teamId: fixture.home_team,
    side: "home",
    random,
    add,
  });
  addGoalEvents({
    count: result.awayScore,
    fixture,
    lineup: away.starters,
    teamId: fixture.away_team,
    side: "away",
    random,
    add,
  });

  for (const side of [home, away]) {
    const chancePlayer = pickAttacker(side.starters, random);
    if (chancePlayer && random() < 0.55) {
      add(
        recordEvent(fixture.id, minuteBetween(12, 88, random), "big_chance", chancePlayer, {
          teamId: side.teamId,
          description: `${chancePlayer.name} finds space for a big chance`,
          metadata: { side: side.label },
        }),
      );
    }

    const substitution = side.substitution;
    if (substitution) {
      add(
        recordEvent(fixture.id, minuteBetween(58, 78, random), "substitution", substitution.in, {
          teamId: side.teamId,
          description: `${substitution.in.name} replaces ${substitution.out.name}`,
          metadata: {
            outPlayerId: substitution.out.player_id,
            inPlayerId: substitution.in.player_id,
            side: side.label,
          },
        }),
      );
    }

    if (side.adaptation) {
      add(
        recordEvent(fixture.id, side.adaptation.minute, "tactical_shift", null, {
          teamId: side.teamId,
          description: `${side.manager?.name || "Manager"} switches to ${side.adaptation.decision}`,
          metadata: {
            decision: side.adaptation.decision,
            side: side.label,
          },
        }),
      );
    }
  }

  if (random() < 0.04) {
    const side = random() < 0.5 ? home : away;
    const player = pickDefender(side.starters, random);
    if (player) {
      add(
        recordEvent(fixture.id, minuteBetween(20, 85, random), "red_card", player, {
          teamId: side.teamId,
          description: `${player.name} is sent off`,
          metadata: { side: side.label },
        }),
      );
    }
  }

  return events
    .sort((a, b) => a.minute - b.minute || a.sequence - b.sequence)
    .map((event, index) => ({
      ...event,
      sequence: index + 1,
    }));
}

function attachPlayerNames(events, playersById = new Map(), teamsById = new Map()) {
  return events.map((event) => {
    const player = playersById.get(String(event.playerId));
    const team = teamsById.get(String(event.teamId));
    return {
      ...event,
      playerName: player?.name || null,
      teamName: team?.name || team?.team_name || null,
    };
  });
}

function getHighlights(events) {
  return events.filter((event) => HIGHLIGHT_TYPES.has(event.type) || event.isHighlight);
}

function mapEventToAnimation(type) {
  return (
    {
      goal: "celebration_goal",
      red_card: "referee_red_card",
      big_chance: "chance_shot",
      substitution: "touchline_substitution",
      tactical_shift: "manager_tactical_adjustment",
      yellow_card: "referee_yellow_card",
    }[type] || "match_event_generic"
  );
}

function addGoalEvents({ count, fixture, lineup, teamId, side, random, add }) {
  const minutes = goalMinutes(count, random);
  for (let index = 0; index < count; index += 1) {
    const scorer = pickAttacker(lineup, random);
    if (!scorer) {
      continue;
    }
    add(
      recordEvent(fixture.id, minutes[index], "goal", scorer, {
        teamId,
        description: `${scorer.name} scores`,
        metadata: { side },
      }),
    );
  }
}

function goalMinutes(count, random) {
  return Array.from({ length: count }, () => minuteBetween(4, 90, random)).sort((a, b) => a - b);
}

function pickAttacker(players, random) {
  return pickWeighted(
    players.filter((player) => ["FW", "MF"].includes(player.position)),
    random,
  );
}

function pickDefender(players, random) {
  return pickWeighted(
    players.filter((player) => ["DF", "MF"].includes(player.position)),
    random,
  );
}

function pickWeighted(players, random) {
  const pool = players.length ? players : [];
  if (!pool.length) {
    return null;
  }
  return pool[Math.floor(random() * pool.length)];
}

function minuteBetween(min, max, random) {
  return min + Math.floor(random() * (max - min + 1));
}

module.exports = {
  attachPlayerNames,
  generateMatchEvents,
  getHighlights,
  mapEventToAnimation,
  recordEvent,
};
