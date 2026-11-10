import { filterCountsKey, useAutoFilters, type CountsFor } from '@/composables/useAutoFilters'
import en from '@/locales/en.json'
import type { DictColumn } from '@/stores/dictionary'
import type { FilterDescriptor } from '@/utils/filterProfile'
import { perfMeasure } from '@/utils/perf'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, inject } from 'vue'
import { createI18n } from 'vue-i18n'

const filteredRowsSync = vi.fn()

vi.mock('@/composables/useDataset', () => ({
  useDataset: () => ({
    filteredRowsSync,
    rowsSync: () => [],
    // Never resolves: these tests read the counts, not the profile.
    ready: () => new Promise(() => {})
  })
}))
vi.mock('@/stores/dictionary', async (original) => ({
  ...(await original<object>()),
  useDictionaryStore: () => ({ fetch: async () => {}, columnsFor: () => [] })
}))
vi.mock('@/utils/perf', () => ({ perfMark: vi.fn(), perfMeasure: vi.fn() }))

const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

const filter: FilterDescriptor = {
  key: 'connection_type',
  column: { name: 'connection_type' } as DictColumn,
  kind: 'categorical',
  distinct: 2,
  nonNull: 8,
  missing: 0,
  notReported: 0,
  notApplicable: 0,
  options: [
    { value: 'RBS', count: 5 },
    { value: 'WUF-W', count: 3 }
  ]
}

/** The function a `FilterInput` gets from a dashboard. */
function mountCountsFor(): CountsFor {
  let counts: CountsFor | undefined
  const Child = defineComponent({
    setup() {
      counts = inject(filterCountsKey)
      return () => null
    }
  })
  const Dashboard = defineComponent({
    setup() {
      useAutoFilters({
        database: 'connections',
        datasetKey: 'connections',
        fetchAll: async () => [],
        i18nPrefix: 'connection.'
      })
      return () => h(Child)
    }
  })
  mount(Dashboard, { global: { plugins: [i18n] } })
  return counts!
}

describe('useAutoFilters countsFor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('counts over the rows of the query it is given', () => {
    filteredRowsSync.mockReturnValue([{ connection_type: 'RBS' }, { connection_type: 'RBS' }])
    const counts = mountCountsFor()(filter, 'd_b:0<<10')
    expect(filteredRowsSync).toHaveBeenCalledWith('d_b:0<<10')
    expect(counts.options).toEqual([
      { value: 'RBS', count: 2, total: 5 },
      { value: 'WUF-W', count: 0, total: 3 }
    ])
  })

  it('writes one measure per count, for the benchmark', () => {
    filteredRowsSync.mockReturnValue([])
    mountCountsFor()(filter, 'd_b:0<<10')
    expect(perfMeasure).toHaveBeenCalledTimes(1)
    expect(perfMeasure).toHaveBeenCalledWith(
      'filters:counts',
      'filters:counts:start',
      'filters:counts:end'
    )
  })

  it('does no work with no other filter: the profile already has the answer', () => {
    const counts = mountCountsFor()(filter, undefined)
    expect(filteredRowsSync).not.toHaveBeenCalled()
    expect(perfMeasure).not.toHaveBeenCalled()
    expect(counts.options?.map((option) => option.total)).toEqual([5, 3])
    expect(counts.options?.map((option) => option.count)).toEqual([5, 3])
  })
})
