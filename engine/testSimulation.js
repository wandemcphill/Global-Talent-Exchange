const { createSampleMatchPackage } = require("./index");

const { timeline, scenes } = createSampleMatchPackage(1337);

console.log(
  JSON.stringify(
    {
      timeline,
      scenes,
    },
    null,
    2,
  ),
);
