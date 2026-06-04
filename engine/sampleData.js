const { Player } = require("./playerModel");
const { Team } = require("./teamModel");
const { simulateMatch } = require("./matchEngine");
const { enhanceTimeline } = require("./narrativeEngine");
const { buildScenes } = require("./sceneBuilder");

function createSampleTeam(side, name, tactic, bias) {
  const template = [
    ["GK", 58, 10, 24, 78, 74],
    ["DF", 63, 30, 74, 70, 64],
    ["DF", 62, 28, 75, 71, 65],
    ["DF", 65, 32, 76, 72, 67],
    ["DF", 64, 34, 77, 73, 68],
    ["MF", 74, 48, 63, 75, 73],
    ["MF", 77, 57, 55, 76, 74],
    ["MF", 75, 56, 57, 77, 75],
    ["FW", 67, 80, 34, 82, 79],
    ["FW", 72, 74, 36, 80, 77],
    ["FW", 71, 73, 38, 79, 76],
  ];

  return new Team({
    id: side,
    name,
    tactic,
    players: template.map(([role, passing, shooting, tackling, positioning, composure], index) =>
      new Player({
        id: `${side}-${index + 1}`,
        name: `${name} ${role}${index + 1}`,
        role,
        passing: passing + (bias.passing || 0),
        shooting: shooting + (bias.shooting || 0),
        tackling: tackling + (bias.tackling || 0),
        positioning: positioning + (bias.positioning || 0),
        composure: composure + (bias.composure || 0),
      }),
    ),
  });
}

function createSampleMatchPackage(seed = 777) {
  const home = createSampleTeam("home", "Kano Pillars", "attacking", {
    passing: 3,
    shooting: 4,
    positioning: 3,
    composure: 2,
  });
  const away = createSampleTeam("away", "Enyimba FC", "balanced", {
    passing: 1,
    shooting: 2,
    tackling: 3,
    positioning: 1,
    composure: 1,
  });

  const timeline = enhanceTimeline(simulateMatch(home, away, seed), {
    isDerby: true,
    transferRumorPlayerId: "away-9",
  });

  return {
    timeline,
    scenes: buildScenes(timeline),
  };
}

module.exports = {
  createSampleTeam,
  createSampleMatchPackage,
};
