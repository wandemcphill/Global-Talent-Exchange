import { defineConfig, devices } from "@playwright/test";

const apiBaseUrl = process.env.GTEX_E2E_API_BASE_URL;
const baseURL = process.env.GTEX_E2E_BASE_URL ?? "http://127.0.0.1:7357";

const webServer = process.env.GTEX_E2E_BASE_URL
  ? undefined
  : apiBaseUrl
    ? {
        command: [
          "flutter run -d web-server --web-hostname 127.0.0.1 --web-port 7357",
          `--dart-define=GTE_API_BASE_URL=${apiBaseUrl}`,
          "--dart-define=GTE_BACKEND_MODE=live",
        ].join(" "),
        cwd: "../../frontend",
        url: baseURL,
        timeout: 180_000,
        reuseExistingServer: !process.env.CI,
      }
    : undefined;

export default defineConfig({
  testDir: "./tests",
  timeout: 120_000,
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  outputDir: "test-results",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer,
  projects: [
    { name: "mobile", use: { ...devices["Pixel 5"] } },
    {
      name: "tablet",
      use: { viewport: { width: 768, height: 1024 }, deviceScaleFactor: 1 },
    },
    {
      name: "desktop",
      use: { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 },
    },
  ],
});
