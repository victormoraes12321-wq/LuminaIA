import { defineConfig, devices } from '@playwright/test'

const reservedPorts = new Set([3000, 3001, 3002, 3333, 8000])
const requestedPort = Number(process.env.PLAYWRIGHT_PORT || '3100')
const dashboardUiTestMode = process.env.PLAYWRIGHT_DASHBOARD_UI_MODE || 'V2_SIDE_CHAT'
const dashboardAiTestMode = process.env.PLAYWRIGHT_DASHBOARD_AI_MODE || 'AI_ASSISTED_EDIT'

if (!Number.isInteger(requestedPort) || requestedPort < 1024 || requestedPort > 65535) {
  throw new Error('PLAYWRIGHT_PORT must be an integer between 1024 and 65535.')
}
if (reservedPorts.has(requestedPort)) {
  throw new Error(`PLAYWRIGHT_PORT ${requestedPort} is reserved for an operational service.`)
}

const testBaseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${requestedPort}`
const parsedBaseURL = new URL(testBaseURL)
const parsedPort = Number(parsedBaseURL.port || (parsedBaseURL.protocol === 'https:' ? 443 : 80))

if (!['127.0.0.1', 'localhost'].includes(parsedBaseURL.hostname)) {
  throw new Error('PLAYWRIGHT_BASE_URL must use loopback.')
}
if (reservedPorts.has(parsedPort)) {
  throw new Error(`PLAYWRIGHT_BASE_URL port ${parsedPort} is reserved for an operational service.`)
}

export default defineConfig({
  testDir: './tests/visual',
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  fullyParallel: true,
  workers: 2,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: testBaseURL,
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `npm run dev:local -- --hostname 127.0.0.1 --port ${requestedPort}`,
    url: testBaseURL,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      ...process.env,
      NEXT_PUBLIC_SUPERVISED_FEEDBACK_ENABLED: 'true',
      NEXT_PUBLIC_SUPERVISED_FEEDBACK_ADMIN_ENABLED: 'true',
      NEXT_PUBLIC_SEMANTIC_RETRIEVAL_ENABLED: 'true',
      DASHBOARD_UI_MODE: dashboardUiTestMode,
      NEXT_PUBLIC_DASHBOARD_UI_MODE: dashboardUiTestMode,
      DASHBOARD_AI_ASSISTANCE_MODE: dashboardAiTestMode,
      NEXT_PUBLIC_DASHBOARD_AI_ASSISTANCE_MODE: dashboardAiTestMode,
    },
  },
  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'tablet',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1180, height: 820 },
        deviceScaleFactor: 2,
        isMobile: false,
        hasTouch: true,
      },
    },
    {
      name: 'mobile',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 390, height: 844 },
        deviceScaleFactor: 3,
        isMobile: true,
        hasTouch: true,
      },
    },
    {
      name: 'ultrawide',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1920, height: 1080 } },
    },
  ],
})
