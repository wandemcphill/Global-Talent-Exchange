const { interpretEvent } = require("./eventInterpreter");

function buildScenes(timeline) {
  const events = timeline && Array.isArray(timeline.events) ? timeline.events : [];
  return {
    matchId: timeline ? timeline.matchId : "unknown",
    seed: timeline ? timeline.seed : 0,
    homeTeam: timeline ? timeline.homeTeam : "Home",
    awayTeam: timeline ? timeline.awayTeam : "Away",
    scenes: events.map((event) => ({
      minute: event.minute,
      ...interpretEvent(event),
    })),
  };
}

module.exports = { buildScenes };
