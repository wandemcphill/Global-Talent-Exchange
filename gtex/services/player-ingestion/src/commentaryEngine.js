"use strict";

function generateCommentary(event, match = {}) {
  const player = event.playerName || event.player || "the player";
  const team = event.teamName || event.team || "the team";
  const minute = Number(event.minute || 0);
  const scoreClose = isScoreClose(match);

  let base;
  switch (String(event.type || event.event || "").toLowerCase()) {
    case "goal":
      base = `${player} finds the net for ${team}.`;
      break;
    case "big_chance":
    case "chance":
      base = `${player} misses a big chance for ${team}.`;
      break;
    case "red_card":
      base = `${player} is sent off. ${team} have to reorganise.`;
      break;
    case "substitution":
      base = event.description || `${team} make a change.`;
      break;
    case "tactical_shift":
      base = event.description || `${team} adjust their shape.`;
      break;
    default:
      base = event.description || `${team} are building the next attack.`;
      break;
  }

  if (minute > 85 && scoreClose) {
    return `Late drama unfolding. ${base}`;
  }
  return varyCommentary(base, event.sequence || minute || 0);
}

function varyCommentary(base, seed = 0) {
  const variants = [base, `Sharp passage of play. ${base}`, `The crowd can feel this. ${base}`];
  return variants[Math.abs(Number(seed) || 0) % variants.length];
}

function buildLiveMatchPayload(event, match = {}) {
  const score = scoreText(match);
  const commentary = event.commentary || generateCommentary(event, match);
  return {
    minute: Number(event.minute || 0),
    event: event.type || event.event || "incident",
    event_type: event.type || event.event || "incident",
    player: event.playerName || event.player || null,
    team: event.teamName || event.team || null,
    score,
    commentary,
    description: commentary,
    title: titleForEvent(event),
    is_key_moment: Boolean(event.isHighlight),
    animation_key: event.animationKey || null,
    audio_url: event.audioUrl || null,
  };
}

function scoreText(match = {}) {
  const home = Number(match.homeScore || match.home_score || 0);
  const away = Number(match.awayScore || match.away_score || 0);
  return `${home}-${away}`;
}

function titleForEvent(event) {
  const team = event.teamName || event.team || "";
  const type = String(event.type || event.event || "incident").replace(/_/g, " ");
  const prefix = team ? `${team} ` : "";
  if (type === "goal") {
    return `${prefix}goal`.trim();
  }
  return `${prefix}${type}`.trim();
}

function isScoreClose(match = {}) {
  const home = Number(match.homeScore || match.home_score || 0);
  const away = Number(match.awayScore || match.away_score || 0);
  return Math.abs(home - away) <= 1;
}

module.exports = {
  buildLiveMatchPayload,
  generateCommentary,
  scoreText,
  varyCommentary,
};
