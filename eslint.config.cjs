const js = require("@eslint/js");
const globals = require("globals");

const isProduction = process.env.NODE_ENV === "production" || process.env.CI === "true";

module.exports = [
  {
    ignores: ["node_modules/**", "design-concepts/**", ".venv/**"],
  },
  js.configs.recommended,
  {
    files: ["**/*.{js,mjs,cjs}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "script",
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      "no-console": isProduction ? "error" : "warn",
      "no-unused-vars": [
        "error",
        {
          args: "after-used",
          argsIgnorePattern: "^_",
          caughtErrors: "all",
          caughtErrorsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
        },
      ],
    },
  },
  // Files ending in .mjs are ECMAScript modules by definition. Keep this
  // override separate so legacy .js and .cjs files retain script parsing.
  {
    files: ["**/*.mjs"],
    languageOptions: {
      sourceType: "module",
    },
  },
  // The humanoid GLB compiler is a Node CLI that emits build and verification
  // output. Keep console output allowed only for this script.
  {
    files: ["frontend/react-shell/scripts/build_humanoid_footballer_glb.mjs"],
    rules: {
      "no-console": "off",
    },
  },
  // Playwright's browser suites are native ES modules. Keeping this narrow
  // prevents their `import` syntax from being parsed as CommonJS while the
  // repository's older JavaScript configuration remains unchanged.
  {
    files: ["qa/playwright/**/*.{js,mjs}"],
    languageOptions: {
      sourceType: "module",
    },
  },
  // The React shell's src/*.js files are ES modules. Config files at the
  // shell root stay CommonJS (`module.exports`).
  {
    files: ["frontend/react-shell/src/**/*.js"],
    languageOptions: {
      sourceType: "module",
    },
  },
];
