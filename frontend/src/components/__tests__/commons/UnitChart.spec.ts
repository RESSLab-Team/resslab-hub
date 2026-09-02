import UnitChart from '@/components/commons/charts/UnitChart.vue'
import { mount } from '@vue/test-utils'
import type { EChartsOption, LegendComponentOption } from 'echarts'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

// vue-echarts is stubbed: the test is about the option handed to it, not
// about what ECharts draws. `useUnits` is left real (it needs a Pinia), its
// inputs are empty.
function legendOf(option: EChartsOption) {
  const wrapper = mount(UnitChart, {
    props: { option },
    global: { stubs: { echarts: true, VResponsive: { template: '<div><slot /></div>' } } }
  })
  // vue-echarts registers itself under the name `echarts`.
  const chart = wrapper.findComponent({ name: 'echarts' })
  return (chart.props('option') as EChartsOption).legend as LegendComponentOption
}

describe('UnitChart legend', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('lists the series in the order given and marks dashed ones', () => {
    const legend = legendOf({
      xAxis: { name: 'x' },
      yAxis: { name: 'y' },
      series: [
        { type: 'line', name: 'measured', data: [[0, 1]] },
        { type: 'line', name: 'model', data: [[0, 1]], lineStyle: { type: 'dashed' } },
        { type: 'line', data: [[0, 1]] }
      ]
    })
    const data = legend.data as { name: string; icon?: string }[]
    expect(data.map((entry) => entry.name)).toEqual(['measured', 'model'])
    expect(data[0].icon).toBeUndefined()
    expect(data[1].icon).toMatch(/^path:\/\//)
  })
})
