import i18n from '@/plugins/i18n'
import { isNotReported } from '@/utils/missing'

/** "Not reported" or "Not applicable" for an empty `field` of `record` (#427). */
export function missingLabel(record: object, field: string): string {
  return i18n.global.t(isNotReported(record, field) ? 'enum.notReported' : 'enum.notApplicable')
}

/** True for the integer types of the data dictionary (`SmallInteger`,
 *  `Integer`, `BigInteger`, and typos like `SmallSmallInteger`). */
export function isIntegerType(type?: string): boolean {
  return !!type && /integer$/i.test(type.trim())
}

/** Most decimals a small value can get. */
const MAX_SMALL_DIGITS = 6

/**
 * A float with at least `minDigits` decimals (#454): 345 gives `345.0`,
 * 40.608 gives `40.6`. A value between 0 and 1 keeps two significant digits,
 * so a ratio or a strain does not become `0.0`: 0.003 gives `0.003`, 0.0456
 * gives `0.046`.
 */
export function formatFloat(value: number, minDigits = 1): string {
  if (!Number.isFinite(value)) return String(value)
  const abs = Math.abs(value)
  if (abs === 0 || abs >= 1) return value.toFixed(minDigits)
  const significant = Math.min(MAX_SMALL_DIGITS, 1 - Math.floor(Math.log10(abs)))
  let text = value.toFixed(Math.max(minDigits, significant))
  // Drop the zeros at the end, down to minDigits: 0.50 gives 0.5.
  while (text.endsWith('0') && text.length - text.indexOf('.') - 1 > minDigits) {
    text = text.slice(0, -1)
  }
  return text
}

/**
 * The number in `field` of `record`. An integer column (from `type`, the
 * column type in the data dictionary) shows with no decimal, any other number
 * with `formatFloat`, at least `fractionDigits` decimals. An empty value says
 * if it was not reported or not applicable, from the record's `not_reported`
 * list.
 */
export function formatNumber<R extends object>(
  record: R,
  field: keyof R & string,
  fractionDigits = 1,
  type?: string
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
  return isIntegerType(type) ? num.toFixed(0) : formatFloat(num, fractionDigits)
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
