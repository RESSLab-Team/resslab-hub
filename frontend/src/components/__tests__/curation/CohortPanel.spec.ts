import type { CurationDetail } from '@/backend'
import CohortPanel from '@/components/curation/CohortPanel.vue'
import type { ParallelSelection } from '@/composables/chart'
import en from '@/locales/en.json'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'

// The panel reads the whole existing database through `useDataset`; a fake lets
// the test assert *which query* each read used, which is the point of the
// brush-as-cohort-filter wiring.
const matrixSync = vi.fn(() => ({ ids: ['B1', 'B2'], data: [[], []] }))
const countRowsSync = vi.fn((query?: string) => (query?.includes('<<') ? 3 : 12))

vi.mock('@/composables/useDataset', () => ({
  useDataset: () => ({
    ready: () => Promise.resolve(),
    matrixSync,
    countRowsSync
  })
}))

// A local instance rather than `@/plugins/i18n`: the plugin reads localStorage at
// import time, which the test environment does not provide.
const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

const DETAIL = {
  pr_number: 7,
  experiments: [{ id: 'NEW-1', cells: { steel: 'S355', cross_section_shape: 'HSS Square' } }]
} as unknown as CurationDetail

const CRITERIA = 'cross_section_shape:HSS Square,'
const BRUSHED = `${CRITERIA};f_y:300<<400`

function mountPanel(brush: ParallelSelection | null = null, cohortQuery = CRITERIA) {
  return mount(CohortPanel, {
    props: {
      database: 'braces' as const,
      detail: DETAIL,
      selectedUid: 0,
      fields: ['cross_section_shape'],
      restrict: true,
      criteriaQuery: CRITERIA,
      cohortQuery,
      brush
    },
    global: {
      plugins: [i18n],
      stubs: { VIcon: true, ToolSwitch: true, SimpleParallelChart: true }
    }
  })
}

function chart(wrapper: ReturnType<typeof mountPanel>) {
  return wrapper.findComponent({ name: 'SimpleParallelChart' })
}

describe('CohortPanel brush wiring', () => {
  beforeEach(() => {
    matrixSync.mockClear()
    countRowsSync.mockClear()
  })

  it('draws the chart on the criteria cohort, not on the brushed subset', async () => {
    const wrapper = mountPanel({ clauses: { f_y: '300<<400' } }, BRUSHED)
    await flushPromises()

    // The brush must not shrink the chart under the curator's own pointer —
    // the bands only stay meaningful over the full criteria domain.
    const queries = matrixSync.mock.calls.map((call) => (call as unknown[])[1])
    expect(queries).toContain(CRITERIA)
    expect(queries).not.toContain(BRUSHED)
  })

  it('pins the submitted specimens so no brush or zoom can grey them out', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    expect(chart(wrapper).props('pinnedIds')).toEqual(['NEW-1'])
    expect(chart(wrapper).props('ids')).toContain('NEW-1')
  })

  it('reports the committed brush upwards', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    const selection: ParallelSelection = { clauses: { f_y: '300<<400' } }
    chart(wrapper).vm.$emit('brush:commit', selection)

    expect(wrapper.emitted('update:brush')?.[0]).toEqual([selection])
  })

  it('reports a cleared brush as no brush at all', async () => {
    const wrapper = mountPanel({ clauses: { f_y: '300<<400' } }, BRUSHED)
    await flushPromises()

    chart(wrapper).vm.$emit('brush:commit', { clauses: {} })

    expect(wrapper.emitted('update:brush')?.[0]).toEqual([null])
  })

  it('marks the chart filtered only while a brush is committed', async () => {
    const plain = mountPanel()
    await flushPromises()
    expect(chart(plain).props('isFiltered')).toBe(false)

    const brushed = mountPanel({ clauses: { f_y: '300<<400' } }, BRUSHED)
    await flushPromises()
    expect(chart(brushed).props('isFiltered')).toBe(true)
  })

  it('zooming redraws the axes on the brushed subset', async () => {
    const wrapper = mountPanel({ clauses: { f_y: '300<<400' } }, BRUSHED)
    await flushPromises()
    matrixSync.mockClear()

    chart(wrapper).vm.$emit('update:zoomed', true)
    await flushPromises()

    const queries = matrixSync.mock.calls.map((call) => (call as unknown[])[1])
    expect(queries).toContain(BRUSHED)
    expect(chart(wrapper).props('zoomed')).toBe(true)
  })

  it('counts the criteria cohort, and the brushed subset beside it', async () => {
    const wrapper = mountPanel({ clauses: { f_y: '300<<400' } }, BRUSHED)
    await flushPromises()

    const banner = wrapper.get('.cohort-h .ct').text()
    expect(banner).toContain('12 similar')
    expect(banner).toContain('3 brushed')
  })

  it('shows no brushed count until something is brushed', async () => {
    const wrapper = mountPanel()
    await flushPromises()

    const banner = wrapper.get('.cohort-h .ct').text()
    expect(banner).toContain('12 similar')
    expect(banner).not.toContain('brushed')
  })
})
