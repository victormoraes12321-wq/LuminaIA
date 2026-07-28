export interface ComparisonRendererFeatureFlags {
  enabled: boolean
  shadowMode: boolean
  source: 'ENVIRONMENT' | 'TEST_OVERRIDE' | 'DEFAULT'
}

const ENABLED_KEY = 'lumina-comparison-renderer-v2'
const SHADOW_KEY = 'lumina-comparison-renderer-v2-shadow'

function testOverride(key: string): boolean | null {
  if (process.env.NODE_ENV === 'production' || typeof window === 'undefined') return null
  try {
    const value = window.localStorage.getItem(key)
    if (value === 'enabled') return true
    if (value === 'disabled') return false
  } catch {
    return null
  }
  return null
}

export function getComparisonRendererFeatureFlags(): ComparisonRendererFeatureFlags {
  const enabledOverride = testOverride(ENABLED_KEY)
  const shadowOverride = testOverride(SHADOW_KEY)
  const enabledFromEnvironment =
    process.env.NEXT_PUBLIC_COMPARISON_RENDERER_V2_ENABLED === 'true'
  const shadowFromEnvironment =
    process.env.NEXT_PUBLIC_COMPARISON_RENDERER_V2_SHADOW_MODE === 'true'
  return {
    enabled: enabledOverride ?? enabledFromEnvironment,
    shadowMode: shadowOverride ?? shadowFromEnvironment,
    source: enabledOverride !== null || shadowOverride !== null
      ? 'TEST_OVERRIDE'
      : enabledFromEnvironment || shadowFromEnvironment
        ? 'ENVIRONMENT'
        : 'DEFAULT',
  }
}
