import LegendChart, { LINE_DOTTED, LINE_SOLID } from '@/components/commons/charts/LegendChart.vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg'
import * as components from 'vuetify/components'

// The same icon set as the app (plugins/vuetify.ts): an icon is SVG path data.
const vuetify = createVuetify({
  components,
  icons: { defaultSet: 'mdi', aliases, sets: { mdi } }
})

function paths() {
  const wrapper = mount(LegendChart, {
    props: {
      modelValue: [
        { label: 'DS1', color: '#0072B2', icon: LINE_SOLID, selected: true },
        { label: 'Univariate', color: 'black', icon: LINE_SOLID, selected: true },
        { label: 'Multivariate', color: 'black', icon: LINE_DOTTED, selected: true }
      ]
    },
    global: { plugins: [vuetify] }
  })
  return wrapper.findAll('svg path').map((path) => path.attributes('d') ?? '')
}

describe('LegendChart swatches', () => {
  it('draws a solid line for univariate and a dotted line for multivariate', () => {
    const [ds, univariate, multivariate] = paths()
    expect(ds).toBe(LINE_SOLID)
    expect(univariate).toBe(LINE_SOLID)
    expect(multivariate).toBe(LINE_DOTTED)
    // One bar for the solid line, several short ones for the dotted line.
    expect(univariate.match(/M/g)).toHaveLength(1)
    expect(multivariate.match(/M/g)!.length).toBeGreaterThan(1)
  })
})
