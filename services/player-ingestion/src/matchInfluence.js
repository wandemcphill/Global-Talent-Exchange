"use strict";

const DAY_MS = 24 * 60 * 60 * 1000;

function mapPlayerUpdate(apiPlayer = {}) {
  const source = apiPlayer.raw || apiPlayer;
  const squad = source.squad || source.squadPlayer || {};
  const player = source.player || source;
  const statistics = firstObject(
    player.statistics,
    source.statistics,
    squad.statistics,
    player.stats,
    source.stats,
    squad.stats,
  );

  return {
    id: firstNumber(player.id, source.id, apiPlayer.playerId),
    minutes: firstNumber(
      apiPlayer.minutesPlayed,
      player.minutes,
      source.minutes,
      squad.minutes,
      statistics?.minutes,
      statistics?.minutes_played,
    ),
    rating: firstNumber(
      apiPlayer.lastMatchRating,
      player.rating,
      source.rating,
      squad.rating,
      statistics?.rating,
      statistics?.average_rating,
      statistics?.avg_rating,
    ),
    injured: firstBoolean(
      apiPlayer.isInjured,
      player.injured,
      player.is_injured,
      source.injured,
      source.is_injured,
      squad.injured,
      squad.is_injured,
      hasInjuryStatus(player.status || source.status || squad.status),
      Boolean(player.injury || source.injury || squad.injury) || null,
    ),
    injuryReturnDate: firstDate(
      apiPlayer.injuryReturnDate,
      player.injury_return_date,
      player.injuryReturnDate,
      source.injury_return_date,
      source.injuryReturnDate,
      squad.injury_return_date,
      squad.injuryReturnDate,
    ),
    teamId: firstNumber(
      apiPlayer.teamId,
      source.teamId,
      source.team_id,
      squad.team_id,
      squad.teamId,
    ),
  };
}

function applyPlayerInfluence(previous = null, player, update = mapPlayerUpdate(player)) {
  const next = {
    form: clamp01(numberOr(previous?.form, player.form, 0.5)),
    sharpness: clamp01(numberOr(previous?.sharpness, player.sharpness, 0.5)),
    isInjured: Boolean(previous?.is_injured ?? player.isInjured ?? false),
    injuryReturnDate: previous?.injury_return_date || player.injuryReturnDate || null,
    minutesPlayed: integerOr(previous?.minutes_played, player.minutesPlayed, 0),
    lastMatchRating: numberOr(previous?.last_match_rating, player.lastMatchRating, 0),
    morale: numberOr(player.morale, previous?.morale, 50),
    transferDetected: false,
    previousTeamId: previous?.team_id || null,
  };

  if (isValidRating(update.rating)) {
    next.form = updateForm(next.form, update.rating);
    next.lastMatchRating = clamp(Number(update.rating), 0, 10);
  }

  if (Number.isFinite(update.minutes)) {
    next.sharpness = updateSharpness(next.sharpness, update.minutes);
    next.minutesPlayed = Math.max(0, Math.round(update.minutes));
  }

  applyInjury(next, update);

  if (previous?.team_id && player.teamId && Number(previous.team_id) !== Number(player.teamId)) {
    next.transferDetected = true;
    next.morale = applyTransferMorale(next.morale);
  }

  return next;
}

function updateForm(currentForm, rating) {
  const normalized = clamp(Number(rating) / 10, 0, 1);
  return clamp01(currentForm * 0.7 + normalized * 0.3);
}

function updateSharpness(currentSharpness, minutes) {
  const delta = Number(minutes) > 0 ? 0.05 : -0.02;
  return clamp01(currentSharpness + delta);
}

function applyInjury(playerState, update) {
  if (update.injured === true) {
    playerState.isInjured = true;
    playerState.injuryReturnDate = update.injuryReturnDate || futureDate(14);
    return;
  }

  if (update.injured === false) {
    playerState.isInjured = false;
    playerState.injuryReturnDate = null;
    return;
  }

  if (playerState.isInjured && playerState.injuryReturnDate) {
    const returnDate = new Date(playerState.injuryReturnDate);
    if (!Number.isNaN(returnDate.getTime()) && returnDate <= new Date()) {
      playerState.isInjured = false;
      playerState.injuryReturnDate = null;
    }
  }
}

function updateTeamStrength(teamPlayers) {
  const available = teamPlayers.filter((player) => !player.is_injured && !player.isInjured);
  const pool = available.length ? available : teamPlayers;
  if (!pool.length) {
    return 50;
  }
  const total = pool.reduce(
    (sum, player) => sum + numberOr(player.overall, 50) * clamp01(numberOr(player.form, 0.5)),
    0,
  );
  return total / pool.length;
}

function effectiveStat(base, form) {
  return numberOr(base, 0) * (0.8 + clamp01(numberOr(form, 0.5)) * 0.4);
}

function buildMatchPlayer(player) {
  const form = clamp01(numberOr(player.form, 0.5));
  const sharpness = clamp01(numberOr(player.sharpness, 0.5));
  const fitness = normalizeUnit(player.fitness, 100);
  return {
    id: player.player_id || player.playerId,
    position: player.position,
    stats: {
      pace: effectiveStat(player.pace, form),
      shooting: effectiveStat(player.shooting, form),
      passing: effectiveStat(player.passing, form),
      dribbling: effectiveStat(player.dribbling, form),
      defending: effectiveStat(player.defending, form),
      physical: effectiveStat(player.physical, form),
    },
    state: {
      form,
      sharpness,
      stamina: fitness * sharpness,
      morale: normalizeUnit(player.morale, 100),
    },
    available: !player.is_injured && !player.isInjured,
  };
}

function staminaDrain(player) {
  const sharpness = clamp01(numberOr(player.state?.sharpness, player.sharpness, 0.5));
  return 0.01 * (1 - sharpness);
}

function postMatchUpdate(player, rating) {
  const moraleDelta = Number(rating) > 7 ? 5 : -3;
  return {
    ...player,
    form: updateForm(clamp01(numberOr(player.form, 0.5)), rating),
    morale: clamp(numberOr(player.morale, 50) + moraleDelta, 0, 100),
    lastMatchRating: clamp(Number(rating) || 0, 0, 10),
  };
}

function applyTransferMorale(morale) {
  const current = numberOr(morale, 50);
  const dip = current <= 1 ? 0.1 : 10;
  return clamp(current - dip, 0, current <= 1 ? 1 : 100);
}

function futureDate(days) {
  return new Date(Date.now() + days * DAY_MS);
}

function hasInjuryStatus(value) {
  if (!value) {
    return null;
  }
  const text = String(value).toLowerCase();
  if (text.includes("injur")) {
    return true;
  }
  if (["fit", "available", "active"].some((token) => text.includes(token))) {
    return false;
  }
  return null;
}

function firstNumber(...values) {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number)) {
      return number;
    }
  }
  return null;
}

function firstBoolean(...values) {
  for (const value of values) {
    if (value === true || value === false) {
      return value;
    }
    if (typeof value === "string") {
      const normalized = value.trim().toLowerCase();
      if (["true", "yes", "1", "injured"].includes(normalized)) {
        return true;
      }
      if (["false", "no", "0", "fit", "available"].includes(normalized)) {
        return false;
      }
    }
  }
  return null;
}

function firstDate(...values) {
  for (const value of values) {
    if (!value) {
      continue;
    }
    const date = new Date(value);
    if (!Number.isNaN(date.getTime())) {
      return date;
    }
  }
  return null;
}

function firstObject(...values) {
  for (const value of values) {
    if (Array.isArray(value) && value.length > 0) {
      return value[0];
    }
    if (value && typeof value === "object") {
      return value;
    }
  }
  return null;
}

function integerOr(...values) {
  return Math.round(numberOr(...values));
}

function numberOr(...values) {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number)) {
      return number;
    }
  }
  return 0;
}

function normalizeUnit(value, scale) {
  const number = numberOr(value, scale);
  return clamp01(number > 1 ? number / scale : number);
}

function isValidRating(value) {
  return Number.isFinite(Number(value)) && Number(value) >= 0 && Number(value) <= 10;
}

function clamp01(value) {
  return clamp(Number(value), 0, 1);
}

function clamp(value, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return min;
  }
  return Math.max(min, Math.min(max, number));
}

module.exports = {
  applyPlayerInfluence,
  buildMatchPlayer,
  effectiveStat,
  mapPlayerUpdate,
  postMatchUpdate,
  staminaDrain,
  updateForm,
  updateSharpness,
  updateTeamStrength,
};
