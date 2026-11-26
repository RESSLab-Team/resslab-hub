import GroupedProperties from '@/components/commons/GroupedProperties.vue'
import i18n from '@/plugins/i18n'
import { useDictionaryStore, type DictColumn } from '@/stores/dictionary'
import { DETAIL_DATABASE_KEY } from '@/utils/detail'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { createVuetify } from 'vuetify'

const group = 'Experimental program details'

function column(name: string, description: string, unit: string, type: DictColumn['type']) {
  return { name, description, symbol: '', unit, type, example: '', nullable: true, group }
}

const columns: DictColumn[] = [
  column('latitude', 'Latitude of testing location', 'Degrees', 'Numeric'),
  column('tw', 'Web thickness', 'mm', 'DecimalFloat'),
  column('flange_nr_data', 'Number of measurement points in flange', 'None', 'SmallInteger'),
  column('fy_mw', 'Measured yield strength (web)', 'MPa', 'DecimalFloat'),
  column('plot_sf', '-', 'None', 'Numeric'),
  column('sigma_0_w', 'Residual stress at web center', 'MPa', 'Numeric'),
  column('eps', 'Measured strain', '-', 'DecimalFloat')
]

const record = {
  latitude: 40.608028,
  tw: 6.35,
  flange_nr_data: 12,
  fy_mw: null,
  plot_sf: 1.25,
  sigma_0_w: -88.33910079,
  eps: 0.00394,
  not_reported: ['fy_mw']
}

function render() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const dictionary = useDictionaryStore()
  dictionary.columns = { residuals: columns }
  dictionary.state = 'ready'
  return mount(GroupedProperties, {
    props: { database: 'residuals', record },
    global: {
      plugins: [pinia, i18n, createVuetify()],
      provide: { [DETAIL_DATABASE_KEY as symbol]: ref('residuals') },
      stubs: { VIcon: true, VTooltip: true }
    }
  })
}

/** The value of a row, without its unit. */
function valueOf(row: ReturnType<ReturnType<typeof render>['find']>): string {
  const unit = row.find('.prop-unit')
  const text = row.find('.prop-val').text()
  return (unit.exists() ? text.slice(0, -unit.text().length) : text).trim()
}

/** Label and value text of each row, after the group is opened. */
async function rows() {
  const wrapper = render()
  await wrapper.find('.gp-head').trigger('click')
  return Object.fromEntries(
    wrapper.findAll('.prop-item').map((row) => [row.find('.prop-name').text(), valueOf(row)])
  )
}

describe('GroupedProperties (#454)', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('uses the dictionary description as the label', async () => {
    const shown = await rows()
    expect(Object.keys(shown)).toContain('Web thickness')
    expect(Object.keys(shown)).toContain('Latitude of testing location')
  })

  it('falls back to the column name when there is no description', async () => {
    expect(Object.keys(await rows())).toContain('Plot sf')
  })

  it('gives every float one decimal, like the top of the drawer', async () => {
    const shown = await rows()
    expect(shown['Latitude of testing location']).toBe('40.6')
    expect(shown['Web thickness']).toBe('6.3')
    expect(shown['Plot sf']).toBe('1.3')
    expect(shown['Residual stress at web center']).toBe('-88.3')
    expect(shown['Measured strain']).toBe('0.0039')
    expect(shown['Number of measurement points in flange']).toBe('12')
  })

  it('still says why an empty cell is empty (#427)', async () => {
    expect((await rows())['Measured yield strength (web)']).toBe('Not reported')
  })
})
