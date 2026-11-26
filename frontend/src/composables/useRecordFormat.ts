import { useDictionaryStore } from '@/stores/dictionary'
import { formatNumber } from '@/utils/formatter'
import type { DatabaseId } from '@/utils/navigation'

/**
 * `formatNumber` for the drawer of one database: it reads the column type
 * from the data dictionary, so an integer column stays an integer (#454).
 * Before the dictionary is loaded, every number gets the float rule; the
 * store is reactive, so the drawer renders again once it is ready.
 */
export function useRecordFormat(database: DatabaseId) {
  const dictionary = useDictionaryStore()
  return function format<R extends object>(
    record: R,
    field: keyof R & string,
    fractionDigits = 1
  ): string {
    return formatNumber(record, field, fractionDigits, dictionary.columnFor(database, field)?.type)
  }
}
