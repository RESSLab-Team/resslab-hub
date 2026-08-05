import i18n from '@/plugins/i18n'
import { useContributionStore } from '@/stores/contribution'
import { useDictionaryStore, type DictColumn } from '@/stores/dictionary'
import ContributeView from '@/views/ContributeView.vue'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} })
}))

const BRACE_COLUMNS: DictColumn[] = [
  {
    name: 'id',
    description: '',
    symbol: '',
    unit: '-',
    type: 'String',
    example: 'B1',
    nullable: false
  }
]

function mountView() {
  return mount(ContributeView, {
    global: {
      plugins: [i18n],
      stubs: {
        'v-icon': true,
        PageHeader: true,
        ExperimentCards: true
      }
    }
  })
}

describe('dev demo banner (?demo=global-issues)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.history.replaceState({}, '', '/contribute/new?demo=global-issues')
  })

  it('injects the global-issues response and shows the panel', async () => {
    const dictionary = useDictionaryStore()
    dictionary.columns = { braces: BRACE_COLUMNS }
    dictionary.state = 'ready'
    const store = useContributionStore()

    const wrapper = mountView()
    store.selectDatabase('braces')
    await nextTick()

    const inject = wrapper.get('[data-testid="demo-inject"]')
    await inject.trigger('click')

    expect(store.status).toBe('fail')
    expect(store.response?.error_count).toBe(2)
    expect(store.globalIssues).toHaveLength(3)
    await nextTick()
    expect(wrapper.find('.global-issues').exists()).toBe(true)
    expect(wrapper.text()).toContain('Missing required columns: investigator')
  })

  it('hides the banner without the query flag', async () => {
    window.history.replaceState({}, '', '/contribute/new')
    const dictionary = useDictionaryStore()
    dictionary.columns = { braces: BRACE_COLUMNS }
    dictionary.state = 'ready'
    useContributionStore().selectDatabase('braces')

    const wrapper = mountView()
    await nextTick()
    expect(wrapper.find('[data-testid="demo-inject"]').exists()).toBe(false)
  })
})
