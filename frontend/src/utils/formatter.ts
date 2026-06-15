import i18n from '@/plugins/i18n'

export function formatNumber(value?: number, fractionDigits = 0): string {
  if (value === null || value === undefined) {
    return i18n.global.t('enum.notApplicable')
  } else if (isNaN(value)) {
    return i18n.global.t('enum.notReported')
  } else {
    return value.toFixed(fractionDigits)
  }
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
