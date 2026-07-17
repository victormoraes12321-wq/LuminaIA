const cp1252ExtraBytes: Record<string, number> = {
  '\u20AC': 0x80,
  '\u201A': 0x82,
  '\u0192': 0x83,
  '\u201E': 0x84,
  '\u2026': 0x85,
  '\u2020': 0x86,
  '\u2021': 0x87,
  '\u02C6': 0x88,
  '\u2030': 0x89,
  '\u0160': 0x8A,
  '\u2039': 0x8B,
  '\u0152': 0x8C,
  '\u017D': 0x8E,
  '\u2018': 0x91,
  '\u2019': 0x92,
  '\u201C': 0x93,
  '\u201D': 0x94,
  '\u2022': 0x95,
  '\u2013': 0x96,
  '\u2014': 0x97,
  '\u02DC': 0x98,
  '\u2122': 0x99,
  '\u0161': 0x9A,
  '\u203A': 0x9B,
  '\u0153': 0x9C,
  '\u017E': 0x9E,
  '\u0178': 0x9F,
}

const mojibakePattern = /(?:Ã|Â|â€|â€œ|â€�|â€™|â€˜|â€¦|â€”|â€“|â†|âœ|â”|â•|Ãƒ)/

function cp1252Bytes(value: string): Uint8Array | null {
  const bytes: number[] = []
  for (const char of value) {
    const code = char.codePointAt(0) ?? 0
    if (code <= 0xff) {
      bytes.push(code)
      continue
    }
    const mapped = cp1252ExtraBytes[char]
    if (mapped === undefined) return null
    bytes.push(mapped)
  }
  return Uint8Array.from(bytes)
}

function decodeMojibakeOnce(value: string): string {
  if (!mojibakePattern.test(value)) return value
  const bytes = cp1252Bytes(value)
  if (!bytes) return fallbackReplace(value)

  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes)
  } catch {
    return fallbackReplace(value)
  }
}

function fallbackReplace(value: string): string {
  return value
    .replaceAll('Ã¡', 'á')
    .replaceAll('Ã ', 'à')
    .replaceAll('Ã¢', 'â')
    .replaceAll('Ã£', 'ã')
    .replaceAll('Ã©', 'é')
    .replaceAll('Ãª', 'ê')
    .replaceAll('Ã­', 'í')
    .replaceAll('Ã³', 'ó')
    .replaceAll('Ã´', 'ô')
    .replaceAll('Ãµ', 'õ')
    .replaceAll('Ãº', 'ú')
    .replaceAll('Ã§', 'ç')
    .replaceAll('Ã', 'Á')
    .replaceAll('Ã€', 'À')
    .replaceAll('Ã‚', 'Â')
    .replaceAll('Ãƒ', 'Ã')
    .replaceAll('Ã‰', 'É')
    .replaceAll('ÃŠ', 'Ê')
    .replaceAll('Ã', 'Í')
    .replaceAll('Ã“', 'Ó')
    .replaceAll('Ã”', 'Ô')
    .replaceAll('Ã•', 'Õ')
    .replaceAll('Ãš', 'Ú')
    .replaceAll('Ã‡', 'Ç')
    .replaceAll('Âº', 'º')
    .replaceAll('Âª', 'ª')
    .replaceAll('â€”', '—')
    .replaceAll('â€“', '–')
    .replaceAll('â†’', '→')
    .replaceAll('âœ“', '✓')
    .replaceAll('âœ—', '✗')
    .replaceAll('â€¢', '•')
    .replaceAll('â€¦', '…')
    .replaceAll('â€˜', '‘')
    .replaceAll('â€™', '’')
    .replaceAll('â€œ', '“')
    .replaceAll('â€�', '”')
}

export function repairTextEncoding(value: string): string {
  let repaired = value
  for (let i = 0; i < 3; i += 1) {
    const next = decodeMojibakeOnce(repaired)
    if (next === repaired) break
    repaired = next
  }
  return repaired
}

export function repairObjectText<T>(value: T): T {
  if (typeof value === 'string') return repairTextEncoding(value) as T
  if (Array.isArray(value)) return value.map(item => repairObjectText(item)) as T
  if (!value || typeof value !== 'object') return value

  const source = value as Record<string, unknown>
  const repaired: Record<string, unknown> = {}
  for (const [key, item] of Object.entries(source)) {
    repaired[key] = repairObjectText(item)
  }
  return repaired as T
}
