const js = require("@eslint/js");
const globals = require("globals");

const isProduction = process.env.NODE_ENV === "production" || process.env.CI === "true";

module.exports = [
  {
    ignores: ["node_modules/**"],
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
  // Playwright's browser suites are native ES modules. Keeping this narrow
  // prevents their `import` syntax from being parsed as CommonJS while the
  // repository's older JavaScript configuration remains unchanged.
  {
    files: ["qa/playwright/**/*.{js,mjs}"],
    languageOptions: {
      sourceType: "module",
    },
  },
];
