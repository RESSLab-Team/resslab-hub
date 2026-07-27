import type { DatabaseId } from '@/utils/navigation'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

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
}

/**
 * The data dictionary, served by `GET /dictionary` and fetched once per
 * session (same pattern as the counts store). It is the single source of truth
 * for the contribution editor's columns, labels, units and validation types.
 */
export const useDictionaryStore = defineStore('dictionary', () => {
  const columns = ref<Partial<Record<DatabaseId, DictColumn[]>>>({})
  const state = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')

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

  return { columns, state, ready, fetch, columnsFor, columnFor }
})
