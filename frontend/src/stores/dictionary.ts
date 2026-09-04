import type { DatabaseId } from '@/utils/navigation'
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

/** Column types carried by the data dictionary (mirrors the backend validator). */
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
  /** Column name — identical to the table column and CSV header. */
  name: string
  description: string
  /** Symbol markup (may contain `<sub>`/`<sup>`), or empty. */
  symbol: string
  /** SI unit string, or `-` when unitless. */
  unit: string
  type: DictType
  /** Example value, used to seed template CSVs. */
  example: string
  /** `false` marks a mandatory field. */
  nullable: boolean
  /**
   * Scientific category of the column, e.g. `Beam section properties`. Arrives
   * once the data repo carries the `group` column of the data dictionaries
   * (RESSLab-Team/resslab-hub-data#46); `groupFor()` prefers it over the rules in
   * `utils/fieldGroups.ts` the moment it does.
   */
  group?: string
}

/** Symbol cleaned for display — markdown code backticks dropped, the `-`
 *  no-symbol sentinel mapped to undefined. */
export function displaySymbol(column: DictColumn): string | undefined {
  const symbol = column.symbol.trim().replace(/^`(.*)`$/, '$1')
  return symbol && symbol !== '-' ? symbol : undefined
}

/** Unit for display — undefined when unitless (`-`, or the literal "None"
 *  some dictionaries carry instead). */
export function displayUnit(column: DictColumn): string | undefined {
  const unit = column.unit.trim()
  return unit && unit !== '-' && unit.toLowerCase() !== 'none' ? unit : undefined
}

/**
 * The data dictionary, served by `GET /dictionary` and fetched once per
 * session (same pattern as the counts store). It is the single source of truth
 * for the contribution editor's columns, labels, units and validation types.
 */
export const useDictionaryStore = defineStore('dictionary', () => {
  const columns = ref<Partial<Record<DatabaseId, DictColumn[]>>>({})
  const state = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')
  /**
   * Contributor guides (the data repo's per-database `README.md`, served by
   * `GET /dictionary/{database}/readme` as raw markdown), fetched on demand and
   * kept for the session. `null` records a database that has none.
   */
  const readmes = ref<Partial<Record<DatabaseId, string | null>>>({})

  /**
   * Resolve once the dictionary is loaded, or has failed to load.
   *
   * `fetch` returns straight away when a request is already in flight, so a
   * caller that needs the columns (loading a submission back into the editor)
   * cannot just await it.
   */
  function whenSettled(): Promise<void> {
    if (state.value === 'ready' || state.value === 'error') return Promise.resolve()
    return new Promise((resolve) => {
      const stop = watch(state, (value) => {
        if (value === 'ready' || value === 'error') {
          stop()
          resolve()
        }
      })
    })
  }

  async function fetch(): Promise<void> {
    if (state.value === 'loading' || state.value === 'ready') return
    state.value = 'loading'
    try {
      // Lazy import keeps axios out of the entry bundle (see stores/counts.ts).
      const { axiosInstance, baseUrl } = await import('@/plugins/axios')
      const { data } = await axiosInstance.get(`${baseUrl}/dictionary`)
      columns.value = data
      state.value = 'ready'
    } catch {
      state.value = 'error'
    }
  }

  const ready = computed(() => state.value === 'ready')

  function columnsFor(database: DatabaseId | null): DictColumn[] {
    return database ? columns.value[database] ?? [] : []
  }

  function columnFor(database: DatabaseId, name: string): DictColumn | undefined {
    return columnsFor(database).find((column) => column.name === name)
  }

  async function fetchReadme(database: DatabaseId): Promise<void> {
    if (database in readmes.value) return
    try {
      const { axiosInstance, baseUrl } = await import('@/plugins/axios')
      const { data } = await axiosInstance.get(`${baseUrl}/dictionary/${database}/readme`)
      readmes.value[database] = data.content
    } catch {
      readmes.value[database] = null
    }
  }

  return {
    columns,
    state,
    ready,
    fetch,
    whenSettled,
    columnsFor,
    columnFor,
    readmes,
    fetchReadme
  }
})
