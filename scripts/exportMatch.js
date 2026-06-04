const fs = require("fs");
const path = require("path");
const { createSampleMatchPackage } = require("../engine");

const seedArg = process.argv[2];
const seed = Number.isFinite(Number(seedArg)) ? Number(seedArg) : 777;
const outputDir = path.resolve(__dirname, "..", "data");
const timelinePath = path.join(outputDir, "sampleMatch.json");
const scenesPath = path.join(outputDir, "sampleScenes.json");

const { timeline, scenes } = createSampleMatchPackage(seed);

fs.mkdirSync(outputDir, { recursive: true });
fs.writeFileSync(timelinePath, JSON.stringify(timeline, null, 2));
fs.writeFileSync(scenesPath, JSON.stringify(scenes, null, 2));

console.log(`Exported timeline to ${timelinePath}`);
console.log(`Exported scenes to ${scenesPath}`);
