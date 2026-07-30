import baseConfig from './playwright.config'


const semanticConfig = {
  ...baseConfig,
  fullyParallel: false,
  workers: 1,
  webServer: {
    command: 'npm run start -- --hostname 127.0.0.1 --port 3100',
    url: 'http://127.0.0.1:3100',
    reuseExistingServer: false,
    timeout: 120_000,
  },
}

export default semanticConfig
