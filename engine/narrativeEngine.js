function enhanceEvent(event, context = {}) {
  if (!event) {
    return event;
  }

  const enriched = { ...event };
  if (context.isDerby && enriched.type === "tackle") {
    enriched.overlay = "DERBY TENSION";
    enriched.commentary =
      enriched.commentary || "A crunching tackle lands in a heated derby.";
  }

  if (context.transferRumorPlayerId && enriched.player === context.transferRumorPlayerId) {
    enriched.overlay = enriched.overlay || "TRANSFER WATCH";
  }

  return enriched;
}

function enhanceTimeline(timeline, context = {}) {
  if (!timeline || !Array.isArray(timeline.events)) {
    return timeline;
  }

  return {
    ...timeline,
    events: timeline.events.map((event) => enhanceEvent(event, context)),
  };
}

module.exports = { enhanceEvent, enhanceTimeline };
