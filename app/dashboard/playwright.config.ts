import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    // Preview the production build — tests run against real compiled output
    command: 'npx vite preview --port 4173',
    url: 'http://localhost:4173/dashboard/',
    reuseExistingServer: false,
    timeout: 15_000,
  },
})
