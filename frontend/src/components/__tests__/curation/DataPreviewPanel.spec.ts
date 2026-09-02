import type { CurationFile } from '@/backend'
import DataPreviewPanel from '@/components/curation/DataPreviewPanel.vue'
import en from '@/locales/en.json'
import { flushPromises, mount } from '@vue/test-utils'
import type { LineSeriesOption } from 'echarts'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'

// The panel reads the submitted file through the curation store and the cohort
// through `useDataset`; both are faked so the test is about what ends up on the
// chart. A four-point strain history is enough for the model to run.
const CSV = ['e_true,Sigma_true', '0,0', '0.002,362', '0.004,430', '0.002,80'].join('\n')

const fetchFileText = vi.fn(() => Promise.resolve(CSV))
vi.mock('@/stores/curation', () => ({
  useCurationStore: () => ({ fetchFileText })
}))

const matrixSync = vi.fn(() => ({ ids: ['MAT-1', 'MAT-2'], data: [[5], [5]] }))
vi.mock('@/composables/useDataset', () => ({
  useDataset: () => ({ ready: () => Promise.resolve(), matrixSync })
}))

const fetchCurve = vi.fn(() => Promise.resolve([[0, 0] as number[], [0.002, 350] as number[]]))
vi.mock('@/components/curation/curves', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/components/curation/curves')>()),
  fetchCurve: (...args: unknown[]) => fetchCurve(...(args as [])),
}))

// A local instance rather than `@/plugins/i18n`: the plugin reads localStorage at
// import time, which the test environment does not provide.
const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

const FILES = [
  {
    path: 'material/cyclic_coupons/stress_strain/MAT-NEW.csv',
    kind: 'timeseries',
    timeseries_dir: 'material/cyclic_coupons/stress_strain',
    experiment_id: 'MAT-NEW'
  }
] as CurationFile[]

const CELLS: Record<string, string> = {
  uvc_e__gpa_: '181.05',
  uvc_sigma__mpa_: '411.11',
  uvc_q__mpa_: '116.38',
  uvc_b: '16.57',
  uvc_d__mpa_: '131.87',
  uvc_a: '188.03',
  uvc_c1__mpa_: '21161.27',
  uvc_g1: '210.44',
  uvc_c2__mpa_: '1706.61',
  uvc_g2: '16.5',
  uvc_phi__prct_: '5.45'
}

async function mountPanel(
  props: Partial<{ database: 'cyclic' | 'braces'; cells: Record<string, string> }> = {}
) {
  const wrapper = mount(DataPreviewPanel, {
    props: {
      database: 'cyclic' as const,
      prNumber: 7,
      files: FILES,
      cells: CELLS,
      ...props
    },
    global: {
      plugins: [i18n],
      stubs: { VIcon: true, UnitLineChart: true, ToolSelect: true }
    }
  })
  await flushPromises()
  return wrapper
}

function series(wrapper: Awaited<ReturnType<typeof mountPanel>>): LineSeriesOption[] {
  return wrapper.findComponent({ name: 'UnitLineChart' }).props('series') as LineSeriesOption[]
}

describe('DataPreviewPanel UVC overlay', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchFileText.mockClear()
    fetchCurve.mockClear()
  })

  it('draws the model beside the submitted curve when every parameter is there', async () => {
    const wrapper = await mountPanel()
    const names = series(wrapper).map((serie) => serie.name)
    expect(names).toEqual(['UVC model', 'MAT-NEW'])
    const model = series(wrapper)[0]
    expect(model.data).toHaveLength(4)
    expect(wrapper.findComponent({ name: 'ToolSwitch' }).exists()).toBe(true)
  })

  it('shows the calibration error next to the toggle', async () => {
    const wrapper = await mountPanel()
    expect(wrapper.text()).toContain('Calibration error φ = 5.45 %')
  })

  it('drops the model series when the toggle is switched off', async () => {
    const wrapper = await mountPanel()
    await wrapper.findComponent({ name: 'ToolSwitch' }).vm.$emit('update:modelValue', false)
    await flushPromises()
    expect(series(wrapper).map((serie) => serie.name)).toEqual(['MAT-NEW'])
  })

  it('offers nothing when a parameter is missing from the row', async () => {
    const cells = { ...CELLS }
    delete cells.uvc_g2
    const wrapper = await mountPanel({ cells })
    expect(wrapper.findComponent({ name: 'ToolSwitch' }).exists()).toBe(false)
    expect(series(wrapper).map((serie) => serie.name)).toEqual(['MAT-NEW'])
  })

  it('says which column a pre-#308 submission is missing', async () => {
    const cells: Record<string, string> = { ...CELLS, uvc_e__mpa_: '206780' }
    delete cells.uvc_e__gpa_
    const wrapper = await mountPanel({ cells })
    expect(wrapper.findComponent({ name: 'ToolSwitch' }).exists()).toBe(false)
    expect(wrapper.text()).toContain('uvc_e__gpa_')
    // and it must not silently read the old MPa column instead
    expect(series(wrapper).map((serie) => serie.name)).toEqual(['MAT-NEW'])
  })

  it('says nothing about the model on the other databases', async () => {
    const wrapper = await mountPanel({ database: 'braces' })
    expect(wrapper.text()).not.toContain('uvc_e__gpa_')
  })

  it('stays out of the other databases', async () => {
    const wrapper = await mountPanel({ database: 'braces' })
    expect(wrapper.findComponent({ name: 'ToolSwitch' }).exists()).toBe(false)
    expect(series(wrapper).every((serie) => serie.name !== 'UVC model')).toBe(true)
  })
})

describe('DataPreviewPanel cohort colours', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    fetchCurve.mockClear()
  })

  it('gives each cohort curve its own colour, distinct from the submission', async () => {
    const wrapper = await mountPanel()
    const select = wrapper.findComponent({ name: 'ToolSelect' })
    await select.vm.$emit('update:modelValue', 'MAT-1')
    await select.vm.$emit('update:modelValue', 'MAT-2')
    await flushPromises()

    const ghosts = series(wrapper).filter((serie) =>
      ['MAT-1', 'MAT-2'].includes(String(serie.name))
    )
    expect(ghosts).toHaveLength(2)
    const colors = ghosts.map((serie) => serie.lineStyle?.color)
    expect(colors[0]).not.toBe(colors[1])
    expect(colors).not.toContain('#e30713')
    expect(colors).not.toContain('#212121')
  })
})
