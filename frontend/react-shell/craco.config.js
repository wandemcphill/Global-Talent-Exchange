const path = require("path");

// Standalone GTEX React shell build. No Emergent overlays or injected runtime scripts.
module.exports = {
  webpack: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  jest: {
    configure: (jestConfig) => {
      // Normalize Windows slashes for glob matching in directories containing dots like .gemini
      jestConfig.testMatch = ["**/src/**/__tests__/**/*.{js,jsx,ts,tsx}", "**/src/**/*.{spec,test}.{js,jsx,ts,tsx}"];
      return jestConfig;
    },
  },
};
