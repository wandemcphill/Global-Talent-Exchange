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
};
