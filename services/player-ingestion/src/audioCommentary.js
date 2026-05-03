"use strict";

const config = require("./config");
const logger = require("./logger");

async function renderAudioCommentary(_text, _context = {}) {
  if (!config.audio.commentaryEnabled) {
    return null;
  }
  if (!config.audio.elevenLabsApiKey || !config.audio.elevenLabsVoiceId) {
    logger.warn("audio commentary requested without ElevenLabs configuration", {
      event: "audio_commentary_unconfigured",
    });
    return null;
  }

  // Launch-safe placeholder: the text commentary path is production-ready.
  // TTS is deliberately opt-in until audio storage/streaming policy is finalized.
  logger.warn("audio commentary is enabled but external TTS rendering is not wired", {
    event: "audio_commentary_deferred",
  });
  return null;
}

module.exports = {
  renderAudioCommentary,
};
