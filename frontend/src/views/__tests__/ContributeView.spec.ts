import type { CurationDetail } from '@/backend'
import { defaultApi } from '@/plugins/axios'
import { useAuthStore } from '@/stores/auth'
import { useContributionStore } from '@/stores/contribution'
import { useDictionaryStore, type DictColumn } from '@/stores/dictionary'
import { postContribution } from '@/utils/submission'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import ContributeView from '@/views/ContributeView.vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import type { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { createVuetify } from 'vuetify'

// A local instance rather than `@/plugins/i18n`: the plugin reads localStorage
// at import time. `vi.hoisted` because `vi.mock` runs before the imports.
const i18n = vi.hoisted(() => ({ value: null as unknown as ReturnType<typeof createI18n> }))
vi.mock('@/plugins/i18n', async () => {
  const { createI18n } = await import('vue-i18n')
  const { default: en } = await import('@/locales/en.json')
  i18n.value = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return { default: i18n.value }
})

vi.mock('@/utils/submission', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/utils/submission')>()),
  postContribution: vi.fn(),
  putContribution: vi.fn()
}))

// jsdom has no CompressionStream; the archive itself is covered by tar tests.
vi.mock('@/utils/tar', () => ({
  buildTarGz: vi.fn(async () => new File(['tar'], 'contribution.tar.gz'))
}))

vi.mock('@/plugins/axios', () => ({
  defaultApi: {
    validateData: vi.fn(async () => ({ data: { valid: true, results: [] } })),
    getContribution: vi.fn(),
    getContributionCurves: vi.fn()
  }
}))

const COLUMNS: DictColumn[] = [
  {
    name: 'id',
    description: '',
    symbol: '',
    unit: '-',
    type: 'String',
    example: 'B1',
    nullable: false
  },
  {
    name: 'investigator',
    description: '',
    symbol: '',
    unit: '-',
    type: 'String',
    example: 'X',
    nullable: false
  }
]

const CURVE = 'Displacement [mm],Force [kN]\n0,0\n1,10\n'
const PR_URL = 'https://github.com/x/pull/7'
const BRANCH = 'contrib/braces/b1-abcd1234'

/** What GitHub holds once the batch below is submitted. */
const DETAIL = {
  pr_number: 7,
  pr_url: PR_URL,
  branch: BRANCH,
  head_sha: 'sha-1',
  type: 'all-braces',
  mine: true,
  experiments: [{ id: 'B1', cells: { id: 'B1', investigator: 'X' } }],
  files: [
    { path: 'braces/steel_braces.csv', kind: 'primary' },
    {
      path: 'braces/force_displacement/B1.csv',
      kind: 'timeseries',
      timeseries_dir: 'braces/force_displacement',
      experiment_id: 'B1'
    }
  ]
} as unknown as CurationDetail

/**
 * A fresh app, as after a page load: new stores (the dictionary and the
 * session already answered), a router on `path`, the view under `<router-view>`.
 */
async function openApp(path: string) {
  setActivePinia(createPinia())
  const dictionary = useDictionaryStore()
  dictionary.columns = { braces: COLUMNS }
  dictionary.state = 'ready'
  const auth = useAuthStore()
  auth.user = {
    id: 'u1',
    email: 'u@example.org',
    email_verified: true,
    display_name: 'Ada',
    role: 'contributor'
  } as never
  auth.status = 'authenticated'

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/contribute/new', name: 'ContributeNew', component: ContributeView },
      {
        path: '/contribute/edit/:prNumber(\\d+)',
        name: 'ContributeEdit',
        component: ContributeView,
        props: true
      },
      { path: '/account', component: { render: () => null } }
    ]
  })
  await router.push(path)
  await router.isReady()

  const wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
    attachTo: document.body,
    global: {
      plugins: [router, i18n.value, createVuetify()],
      stubs: {
        'v-icon': true,
        ExperimentCards: true,
        ContributionGuide: true,
        FailureDetails: true,
        ProgressLine: true
      }
    }
  })
  await flushPromises()
  return { router, wrapper, store: useContributionStore() }
}

function buttonWith(wrapper: Awaited<ReturnType<typeof openApp>>['wrapper'], label: string) {
  const button = wrapper.findAll('button').find((b) => b.text().trim() === label)
  if (!button) throw new Error(`no "${label}" button`)
  return button
}

describe('ContributeView after a submit (#403)', () => {
  beforeEach(() => {
    // jsdom has no matchMedia; the view reads it to dock the guide.
    window.matchMedia = vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn()
    }) as never
    vi.mocked(postContribution).mockReset()
    vi.mocked(defaultApi.getContribution).mockReset()
    vi.mocked(defaultApi.getContributionCurves).mockReset()
    vi.mocked(postContribution).mockResolvedValue({
      pr_url: PR_URL,
      pr_number: 7,
      branch: BRANCH,
      head_sha: 'sha-1'
    })
    vi.mocked(defaultApi.getContribution).mockResolvedValue({ data: DETAIL } as never)
    vi.mocked(defaultApi.getContributionCurves).mockResolvedValue({
      data: {
        pr_number: 7,
        head_sha: 'sha-1',
        files: [{ path: 'braces/force_displacement/B1.csv', text: CURVE }]
      }
    } as never)
  })

  it('shows the same submission when the page is refreshed', async () => {
    // A new batch, submitted from the editor.
    const first = await openApp('/contribute/new')
    first.store.selectDatabase('braces')
    first.store.addRow()
    first.store.settle()
    const row = first.store.rows[0]
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
    first.store.attachSeries(row.uid, timeSeriesKindsFor('braces')[0], 'B1.csv', CURVE)
    await nextTick()
    first.store.status = 'pass'
    await nextTick()

    await buttonWith(first.wrapper, 'Submit for review').trigger('click')
    await buttonWith(first.wrapper, 'Submit').trigger('click')
    await flushPromises()

    // The page is now the submission's own page, without a reload.
    const url = first.router.currentRoute.value.fullPath
    expect(url).toBe('/contribute/edit/7')
    expect(defaultApi.getContribution).not.toHaveBeenCalled()
    const before = first.wrapper.text()
    expect(before).toContain('Edit submission #7')
    expect(before).toContain('You are editing submission #7')
    expect(before).toContain('Review request #7 is open')
    expect(first.wrapper.find(`a[href="${PR_URL}"]`).exists()).toBe(true)
    const rowsBefore = first.store.rows.map((r) => ({ ...r.cells }))
    const curvesBefore = Object.keys(first.store.timeSeries).length
    first.wrapper.unmount()

    // The refresh: nothing survives but the URL.
    const second = await openApp(url)
    // The curation store imports the API client lazily: more than one flush.
    await vi.waitFor(() => expect(second.store.loadStatus).toBe('ready'))
    await flushPromises()

    expect(defaultApi.getContribution).toHaveBeenCalledWith(7)
    expect(second.store.editTarget).toEqual({
      prNumber: 7,
      prUrl: PR_URL,
      headSha: 'sha-1',
      branch: BRANCH
    })
    expect(second.store.rows.map((r) => ({ ...r.cells }))).toEqual(rowsBefore)
    expect(Object.keys(second.store.timeSeries)).toHaveLength(curvesBefore)
    expect(second.store.csvOnGitHubUrl).toContain(BRANCH)
    const after = second.wrapper.text()
    expect(after).toContain('Edit submission #7')
    expect(after).toContain('You are editing submission #7')
    expect(second.wrapper.find(`a[href="${PR_URL}"]`).exists()).toBe(true)
    expect(second.router.currentRoute.value.fullPath).toBe('/contribute/edit/7')
    second.wrapper.unmount()
  })
})
