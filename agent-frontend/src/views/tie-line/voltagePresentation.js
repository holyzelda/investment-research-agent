const VOLTAGE_TOKENS = [
  '--xc-map-voltage-1',
  '--xc-map-voltage-2',
  '--xc-map-voltage-3',
  '--xc-map-voltage-4',
  '--xc-map-voltage-5',
]
const UNKNOWN_VOLTAGE_TOKEN = '--xc-map-voltage-unknown'

export function parseVoltageKv(voltageText) {
  if (typeof voltageText !== 'string') return null
  const match = voltageText.replace(/,/g, '').match(/(\d+(?:\.\d+)?)\s*(?:k\s*v|kv)/i)
  return match ? Number(match[1]) : null
}

// 电压为有序工程量：按额定 kV 从低到高映射同一暖色阶，不能使用通用多分类色盘。
export function buildVoltagePresentation(voltageOptions = []) {
  const uniqueOptions = [...new Set(voltageOptions.filter((option) => typeof option === 'string' && option))]
  const known = uniqueOptions
    .map((text) => ({ text, kv: parseVoltageKv(text) }))
    .filter((item) => item.kv !== null)
    .sort((a, b) => b.kv - a.kv || a.text.localeCompare(b.text, 'zh-CN'))
  const unknown = uniqueOptions
    .filter((text) => parseVoltageKv(text) === null)
    .sort((a, b) => a.localeCompare(b, 'zh-CN'))

  const tokenByText = {}
  const knownCount = known.length
  known.forEach((item, index) => {
    const tokenIndex = knownCount <= 1
      ? VOLTAGE_TOKENS.length - 1
      : Math.round(((knownCount - 1 - index) * (VOLTAGE_TOKENS.length - 1)) / (knownCount - 1))
    tokenByText[item.text] = VOLTAGE_TOKENS[tokenIndex]
  })
  unknown.forEach((text) => {
    tokenByText[text] = UNKNOWN_VOLTAGE_TOKEN
  })

  return {
    tokenByText,
    legendItems: [
      ...known.map((item) => ({ ...item, token: tokenByText[item.text] })),
      ...unknown.map((text) => ({ text, kv: null, token: UNKNOWN_VOLTAGE_TOKEN })),
    ],
  }
}
