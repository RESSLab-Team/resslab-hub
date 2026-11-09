import PropertyItem from '@/components/commons/PropertyItem.vue'
import { useDictionaryStore, type DictColumn } from '@/stores/dictionary'
import { DETAIL_DATABASE_KEY } from '@/utils/detail'
import type { DatabaseId } from '@/utils/navigation'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { ref } from 'vue'

const COLUMNS: DictColumn[] = [
  {
    name: 't_t',
    description: 'Gusset plate thickness',
    symbol: 't<sub>t</sub>',
    unit: 'mm',
    type: 'Numeric',
    example: '12',
    nullable: true
  },
  {
    name: 'steel',
    description: '-',
    symbol: '-',
    unit: '-',
    type: 'String',
    example: 'S355',
    nullable: true
  }
]

// Renders the activator and the content side by side, so the test can read the
// tooltip text without opening a real overlay.
const TooltipStub = {
  template: '<div><slot name="activator" :props="{}" /><div class="tip"><slot /></div></div>'
}

// `null` for no drawer: a default parameter would swallow an explicit `undefined`.
function mountItem(column: string | undefined, database: DatabaseId | null = 'braces') {
  return mount(PropertyItem, {
    props: { name: 'Label', unit: 'mm', column },
    slots: { default: '12' },
    global: {
      provide: { [DETAIL_DATABASE_KEY as symbol]: ref(database ?? undefined) },
      stubs: { 'v-tooltip': TooltipStub }
    }
  })
}

describe('PropertyItem glossary tooltip (#330)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const dictionary = useDictionaryStore()
    dictionary.columns = { braces: COLUMNS }
    dictionary.state = 'ready'
  })

  it('shows the description, symbol and unit of a known column', () => {
    const wrapper = mountItem('t_t')
    expect(wrapper.find('.prop-name.has-definition').text()).toBe('Label')
    expect(wrapper.find('.prop-def').text()).toBe('Gusset plate thickness')
    expect(wrapper.find('.prop-def-meta').text()).toBe('tt · mm')
    expect(wrapper.find('.prop-def-meta sub').text()).toBe('t')
  })

  it('shows a plain label without a column', () => {
    const wrapper = mountItem(undefined)
    expect(wrapper.find('.has-definition').exists()).toBe(false)
    expect(wrapper.find('.tip').exists()).toBe(false)
    expect(wrapper.find('.prop-name').text()).toBe('Label')
  })

  it('shows a plain label when the dictionary has no description', () => {
    expect(mountItem('steel').find('.has-definition').exists()).toBe(false)
    expect(mountItem('unknown').find('.has-definition').exists()).toBe(false)
  })

  it('shows a plain label outside a drawer', () => {
    expect(mountItem('t_t', null).find('.has-definition').exists()).toBe(false)
  })
})

describe('PropertyItem label (#328)', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders a dictionary symbol with a real subscript', () => {
    const wrapper = mount(PropertyItem, { props: { name: 'd<sub>pz</sub>' } })
    expect(wrapper.find('.prop-name sub').text()).toBe('pz')
    expect(wrapper.find('.prop-name').text()).toBe('dpz')
  })

  it('renders a plain label as text', () => {
    const wrapper = mount(PropertyItem, { props: { name: 'Beam section' } })
    expect(wrapper.find('.prop-name').text()).toBe('Beam section')
    expect(wrapper.find('.prop-name sub').exists()).toBe(false)
  })
})
