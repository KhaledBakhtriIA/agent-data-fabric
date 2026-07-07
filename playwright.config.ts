import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  retries: 2,
  use: {
    trace: 'on-first-retry',
  },
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/report.json' }],
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
