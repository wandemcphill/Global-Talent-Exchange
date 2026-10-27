const path = require("path");

// Standalone GTEX React shell build. No Emergent overlays or injected runtime scripts.
module.exports = {
  webpack: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  devServer: (devServerConfig) => {
    devServerConfig.historyApiFallback = true;
    return devServerConfig;
  },
  jest: {
    configure: (jestConfig) => {
      // Normalize Windows slashes for glob matching in directories containing dots like .gemini
      jestConfig.testMatch = [
        "**/src/**/__tests__/**/*.{js,jsx,ts,tsx}",
        "**/src/**/*.{spec,test}.{js,jsx,ts,tsx}",
      ];
      jestConfig.moduleNameMapper = {
        ...(jestConfig.moduleNameMapper || {}),
        "^@/(.*)$": "<rootDir>/src/$1",
      };
      return jestConfig;
    },
  },
};
