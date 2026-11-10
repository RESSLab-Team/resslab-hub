import i18n from '@/plugins/i18n'
import { isNotReported } from '@/utils/missing'

/** "Not reported" or "Not applicable" for an empty `field` of `record` (#427). */
export function missingLabel(record: object, field: string): string {
  return i18n.global.t(isNotReported(record, field) ? 'enum.notReported' : 'enum.notApplicable')
}

/**
 * The number in `field` of `record`, with `fractionDigits` decimals. An empty
 * value says if it was not reported or not applicable, from the record's
 * `not_reported` list.
 */
export function formatNumber<R extends object>(
  record: R,
  field: keyof R & string,
  fractionDigits = 0
): string {
  const value = record[field] as unknown
  if (value === null || value === undefined) {
    return missingLabel(record, field)
  }
  // Defensive coercion: all numeric fields are JSON numbers since the backend
  // dropped Decimal serialization, but tolerate strings from older payloads.
  const num = typeof value === 'number' ? value : Number(value)
  if (isNaN(num)) {
    return i18n.global.t('enum.notReported')
  }
  return num.toFixed(fractionDigits)
}

export function formatString(value?: string | null): string {
  if (value === null || value === undefined) {
    return i18n.global.t('enum.notApplicable')
  } else if (value === 'NR') {
    return i18n.global.t('enum.notReported')
  } else {
    return value
  }
}
