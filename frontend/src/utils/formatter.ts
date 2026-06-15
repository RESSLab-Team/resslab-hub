import i18n from '@/plugins/i18n'

export function formatNumber(value?: number, fractionDigits = 0): string {
  if (value === null || value === undefined) {
    return i18n.global.t('enum.notApplicable')
  }
  // Numeric fields can arrive as strings (Pydantic v2 serializes Decimal as a
  // JSON string), so coerce before calling number methods.
  const num = typeof value === 'number' ? value : Number(value)
  if (isNaN(num)) {
    return i18n.global.t('enum.notReported')
  }
  return num.toFixed(fractionDigits)
}

export function formatString(value?: string): string {
  if (value === null || value === undefined) {
    return i18n.global.t('enum.notApplicable')
  } else if (value === 'NR') {
    return i18n.global.t('enum.notReported')
  } else {
    return value
  }
}
