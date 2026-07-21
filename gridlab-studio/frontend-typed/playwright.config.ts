import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  workers: 1,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:8013",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "python ../../tools/run_studio_for_browser.py --port 8013",
    url: "http://127.0.0.1:8013/api/health",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
