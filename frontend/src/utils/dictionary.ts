/**
 * Access to the baked data dictionary (`assets/contribute/dictionary.json`).
 *
 * The JSON is generated from the data repository's `*_data_dictionary.csv`
 * files by `backend/data/generate_dictionary.py` (run via `make generate-model`).
 * It is the single source of truth for the contribution wizard's column set,
 * labels, units, symbols, example values and required flags — the same
 * dictionaries that drive the backend's ORM/validator, so the columns match
 * `__table__.c` by construction.
 */

import rawDictionary from '@/assets/contribute/dictionary.json'
import type { DatabaseId } from '@/utils/navigation'

/** SQL-ish type tags carried by each column, matching the data dictionary. */
export type DictType =
  | 'String'
  | 'Boolean'
  | 'SmallInteger'
  | 'Integer'
  | 'BigInteger'
  | 'Numeric'
  | 'DecimalFloat'
  | 'Date'

export interface DictColumn {
  /** Column name — identical to the ORM column key and CSV header. */
  name: string
  /** Human description, shown as a tooltip. */
  description: string
  /** Markdown-ish symbol (may contain `<sub>`/`<sup>`), or empty. */
  symbol: string
  /** SI unit string, or `-` when unitless. */
  unit: string
  type: DictType
  /** Example value from the dictionary, used to seed template CSVs. */
  example: string
  /** `false` marks a mandatory field (non-nullable column). */
  nullable: boolean
}

const DICTIONARY = rawDictionary as Record<DatabaseId, DictColumn[]>

export function dictionaryFor(database: DatabaseId): DictColumn[] {
  return DICTIONARY[database] ?? []
}

const BY_NAME: Partial<Record<DatabaseId, Map<string, DictColumn>>> = {}

export function columnFor(database: DatabaseId, name: string): DictColumn | undefined {
  let index = BY_NAME[database]
  if (!index) {
    index = new Map(dictionaryFor(database).map((column) => [column.name, column]))
    BY_NAME[database] = index
  }
  return index.get(name)
}
