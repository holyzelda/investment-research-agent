export function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined || value === '') return '—'
  const number = Number(value)
  if (!Number.isFinite(number)) return String(value)
  return Number.isInteger(number) ? String(number) : number.toFixed(decimals)
}

export const formatPrice = (value) => formatNumber(value, 4)
