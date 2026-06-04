function interpretEvent(event) {
  if (!event || !event.type) {
    return {
      type: "COMMENTARY_SCENE",
      duration: 0.8,
      commentary: "",
    };
  }

  switch (event.type) {
    case "pass":
      return {
        type: "PASS_SCENE",
        duration: 1.1,
        actors: [event.from, event.to],
        commentary: event.commentary || "",
      };
    case "through_pass":
      return {
        type: "THROUGH_PASS_SCENE",
        duration: 1.25,
        actors: [event.from, event.to],
        commentary: event.commentary || "",
      };
    case "dribble":
      return {
        type: "DRIBBLE_SCENE",
        duration: event.duration || 1.1,
        actor: event.player,
        commentary: event.commentary || "",
      };
    case "shot":
      return {
        type: "SHOT_SCENE",
        duration: event.duration || 1.2,
        actor: event.player,
        outcome: event.outcome || "",
        commentary: event.commentary || "",
      };
    case "goal":
      return {
        type: "GOAL_SCENE",
        duration: 1.35,
        actor: event.player,
        commentary: event.commentary || "",
      };
    case "save":
      return {
        type: "SAVE_SCENE",
        duration: 1.0,
        actor: event.player,
        commentary: event.commentary || "",
      };
    case "tackle":
      return {
        type: "TACKLE_SCENE",
        duration: 0.9,
        actors: [event.player, event.target],
        commentary: event.commentary || "",
      };
    case "foul":
      return {
        type: "FOUL_SCENE",
        duration: 0.9,
        actors: [event.player, event.target],
        commentary: event.commentary || "",
      };
    default:
      return {
        type: "COMMENTARY_SCENE",
        duration: 0.8,
        commentary: event.commentary || "",
      };
  }
}

module.exports = { interpretEvent };
