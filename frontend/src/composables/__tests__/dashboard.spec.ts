import { useDashboard, withFieldClause } from '@/composables/dashboard'
import { useNotificationStore } from '@/stores/notification'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter, useRoute, useRouter, type Router } from 'vue-router'

// A local instance rather than `@/plugins/i18n`, like SimpleTable.spec.ts.
vi.mock('@/plugins/i18n', async () => {
  const { createI18n } = await import('vue-i18n')
  const { default: en } = await import('@/locales/en.json')
  return { default: createI18n({ legacy: false, locale: 'en', messages: { en } }) }
})

describe('dashboard.withFieldClause', () => {
  it('appends the clause to an empty query', () => {
    expect(withFieldClause(undefined, 'd_b', '200<<400')).toBe('d_b:200<<400')
  })

  it('replaces an existing clause for the field and keeps the others', () => {
    expect(withFieldClause('steel_b:=A992;d_b:0<<100', 'd_b', '200<<400')).toBe(
      'steel_b:=A992;d_b:200<<400'
    )
  })

  it('drops the clause when the value is undefined', () => {
    expect(withFieldClause('steel_b:=A992;d_b:0<<100', 'd_b', undefined)).toBe('steel_b:=A992')
    expect(withFieldClause('d_b:0<<100', 'd_b', undefined)).toBeUndefined()
  })

  it('matches the field by its full key, not a prefix', () => {
    expect(withFieldClause('d_bg:1<<2', 'd_b', '3<<4')).toBe('d_bg:1<<2;d_b:3<<4')
  })
})

interface TestModel {
  id: string
  connection_type: string
  t_dp_tot: number
}

const rows: TestModel[] = [
  { id: '1', connection_type: 'WUF-W', t_dp_tot: 10 },
  { id: '2', connection_type: 'RBS', t_dp_tot: 30 },
  { id: '3', connection_type: 'WUF-W', t_dp_tot: 20 }
]
const TestField = { id: 'id', connection_type: 'connection_type', t_dp_tot: 't_dp_tot' }

// The useDataset cache is module wide and never expires: one key per test.
let keySeq = 0

type Dashboard = ReturnType<typeof useDashboard<TestModel>>

// Mount a page that calls useDashboard, opened at `url`.
async function openPage(url: string): Promise<{ dashboard: Dashboard; router: Router }> {
  let dashboard: Dashboard | undefined
  const Page = defineComponent({
    setup() {
      dashboard = useDashboard<TestModel>(useRoute(), useRouter(), TestField, {
        key: `dashboard-test-${keySeq++}`,
        fetchAll: async () => rows
      })
      return () => null
    }
  })
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/db', component: Page }]
  })
  await router.push(url)
  await router.isReady()
  mount(Page, { global: { plugins: [router] } })
  await settle()
  return { dashboard: dashboard!, router }
}

// Let the dataset load and the 80 ms URL sync run.
async function settle(): Promise<void> {
  await flushPromises()
  await vi.advanceTimersByTimeAsync(200)
  await flushPromises()
}

describe('useDashboard filters in the URL', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('keeps an exact value with a comma in one piece through the URL', async () => {
    const { dashboard, router } = await openPage('/db')
    dashboard.changeSearches('connection_type', '=Fell, Kanvinde & Deierlein')
    await settle()
    expect(router.currentRoute.value.query.connection_type).toBe('=Fell, Kanvinde & Deierlein')
    expect(dashboard.searches.value.connection_type).toBe('=Fell, Kanvinde & Deierlein')
  })

  it('reads the same value from a shared link', async () => {
    const url = `/db?connection_type=${encodeURIComponent('=Fell, Kanvinde & Deierlein')}`
    const { dashboard } = await openPage(url)
    expect(dashboard.searches.value.connection_type).toBe('=Fell, Kanvinde & Deierlein')
  })

  it('still reads a bare value with a comma as a set', async () => {
    const { dashboard } = await openPage(`/db?connection_type=${encodeURIComponent('RBS,WUF-W')}`)
    expect(dashboard.searches.value.connection_type).toEqual(['RBS', 'WUF-W'])
  })
})

describe('useDashboard specimen link (#417)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('opens the specimen of the link, even when its filters hide it', async () => {
    const { dashboard, router } = await openPage('/db?connection_type=WUF-W&specimen=2')
    expect(dashboard.item.value?.id).toBe('2')
    expect(router.currentRoute.value.query).toEqual({ connection_type: 'WUF-W', specimen: '2' })
  })

  it('writes the clicked row into the URL and keeps the filters and the search', async () => {
    const { dashboard, router } = await openPage('/db?connection_type=WUF-W&search=W')
    dashboard.clickTableRow(rows[0])
    await settle()
    expect(router.currentRoute.value.query).toEqual({
      connection_type: 'WUF-W',
      search: 'W',
      specimen: '1'
    })
  })

  it('keeps the specimen when a filter changes', async () => {
    const { dashboard, router } = await openPage('/db?specimen=3')
    dashboard.changeSearches('t_dp_tot', '0<<25')
    await settle()
    expect(router.currentRoute.value.query).toEqual({ t_dp_tot: '0<<25', specimen: '3' })
    expect(dashboard.item.value?.id).toBe('3')
  })

  it('drops the specimen from the URL when the drawer closes', async () => {
    const { dashboard, router } = await openPage('/db?connection_type=RBS&specimen=2')
    dashboard.closeDetail()
    await settle()
    expect(dashboard.item.value).toBeUndefined()
    expect(router.currentRoute.value.query).toEqual({ connection_type: 'RBS' })
  })

  it('closes the drawer on a link to the same page without the specimen', async () => {
    const { dashboard, router } = await openPage('/db?specimen=2')
    await router.push('/db')
    await settle()
    expect(dashboard.item.value).toBeUndefined()
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('tells the user when the specimen does not exist, and drops it', async () => {
    const { dashboard, router } = await openPage('/db?connection_type=RBS&specimen=nope')
    expect(dashboard.item.value).toBeUndefined()
    expect(router.currentRoute.value.query).toEqual({ connection_type: 'RBS' })
    expect(useNotificationStore().message).toBe('Specimen nope was not found.')
  })
})
