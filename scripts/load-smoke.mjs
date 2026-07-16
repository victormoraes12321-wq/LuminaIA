#!/usr/bin/env node

const baseUrl = process.env.LUMINA_BASE_URL || 'http://127.0.0.1:8000'
const path = process.env.LUMINA_LOAD_PATH || '/health'
const totalRequests = Number(process.env.LUMINA_LOAD_REQUESTS || 50)
const concurrency = Number(process.env.LUMINA_LOAD_CONCURRENCY || 5)
const timeoutMs = Number(process.env.LUMINA_LOAD_TIMEOUT_MS || 10_000)

const target = new URL(path, baseUrl).toString()
const durations = []
let ok = 0
let failed = 0
let issued = 0

async function hit() {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  const start = performance.now()
  try {
    const response = await fetch(target, { signal: controller.signal })
    const duration = performance.now() - start
    durations.push(duration)
    if (response.ok) {
      ok += 1
    } else {
      failed += 1
    }
  } catch {
    failed += 1
  } finally {
    clearTimeout(timeout)
  }
}

async function worker() {
  while (issued < totalRequests) {
    issued += 1
    await hit()
  }
}

await Promise.all(Array.from({ length: concurrency }, () => worker()))

durations.sort((a, b) => a - b)
const percentile = p => durations[Math.min(durations.length - 1, Math.floor(durations.length * p))] || 0
const avg = durations.reduce((sum, value) => sum + value, 0) / Math.max(1, durations.length)

const report = {
  target,
  totalRequests,
  concurrency,
  ok,
  failed,
  avgMs: Math.round(avg),
  p95Ms: Math.round(percentile(0.95)),
  maxMs: Math.round(durations[durations.length - 1] || 0),
}

console.log(JSON.stringify(report, null, 2))

if (failed > 0) {
  process.exitCode = 1
}
