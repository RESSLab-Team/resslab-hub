import type {
  BraceField,
  ColumnField,
  ConnectionField,
  HSSColumnField,
  MaterialField
} from '@/backend'
import { kpiSnapshot, type KpiStatus } from '@/utils/kpiSnapshot'
import type { DatabaseId } from '@/utils/navigation'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

// The API client is imported lazily inside fetch(): this store is reachable
// from the entry bundle (App → sidebar badges), and a static import here would
// pull axios + the whole generated client (~1/5 of the old entry chunk) into
// the first paint for what is a decorative, post-mount fetch. The '@/backend'
// imports above are type-only, so they cost nothing at runtime.
type Apis = typeof import('@/plugins/axios')

const fetcherFor: Record<DatabaseId, (apis: Apis) => Promise<{ data: number }>> = {
  connections: (apis) => apis.connectionsApi.getConnectionsDistinct(),
  columns: (apis) => apis.columnsApi.getColumnsDistinct(),
  braces: (apis) => apis.bracesApi.getBracesDistinct(),
  hss: (apis) => apis.hssApi.getHssColumnsDistinct(),
  ebf: (apis) => apis.ebfApi.getEccentricBracedFramesDistinct(),
  cyclic: (apis) => apis.materialsApi.getMaterialsDistinct(),
  tensile: (apis) => apis.tensileCouponApi.getTensileCouponsDistinct(),
  'ductile-fracture': (apis) => apis.ductileFractureApi.getDuctileFracturesDistinct(),
  residuals: (apis) => apis.residualsApi.getResidualStressesDistinct()
}

// Same endpoints narrowed to each database's "who ran the tests" column, so the
// count is distinct experimental programs / investigators — the tiles' "sources".
// Field names are string literals (they satisfy the generated union types) so this
// module keeps its no-static-client-import property.
const sourcesFetcherFor: Record<DatabaseId, (apis: Apis) => Promise<{ data: number }>> = {
  connections: (apis) => apis.connectionsApi.getConnectionsDistinct(['experimental_program']),
  columns: (apis) => apis.columnsApi.getColumnsDistinct(['experimental_program']),
  braces: (apis) => apis.bracesApi.getBracesDistinct(['investigator']),
  hss: (apis) => apis.hssApi.getHssColumnsDistinct(['reference']),
  ebf: (apis) => apis.ebfApi.getEccentricBracedFramesDistinct(['investigator']),
  cyclic: (apis) => apis.materialsApi.getMaterialsDistinct(['experimental_program']),
  tensile: (apis) => apis.tensileCouponApi.getTensileCouponsDistinct(['experimental_program']),
  'ductile-fracture': (apis) =>
    apis.ductileFractureApi.getDuctileFracturesDistinct(['experimental_program']),
  residuals: (apis) => apis.residualsApi.getResidualStressesDistinct(['experimental_program'])
}

// Live KPI values fetched earlier in this browser session. Seeding from this
// cache (instead of only the committed snapshot) means revisiting or reloading
// the home page shows the settled numbers immediately, and the loading bar +
// count-up animation only plays the first time the KPIs are actually loaded.
const CACHE_KEY = 'resslab-kpi-cache'

interface KpiCache {
  counts: Partial<Record<DatabaseId, number>>
  sources: Partial<Record<DatabaseId, number>>
  universities?: number
  users?: number
}

function readCache(): KpiCache {
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(CACHE_KEY) ?? 'null')
    return { counts: {}, sources: {}, ...(typeof parsed === 'object' ? parsed : null) }
  } catch {
    return { counts: {}, sources: {} }
  }
}

/** Test and source counts per database, fetched once per session (sidebar, home tiles). */
export const useCountsStore = defineStore('counts', () => {
  const cache = readCache()

  // Seeded from the committed snapshot, overlaid with any live values from
  // earlier in this session, so tiles and badges render on first paint; each
  // live response then overwrites its key in place.
  const counts = ref<Partial<Record<DatabaseId, number>>>({
    ...kpiSnapshot.counts,
    ...cache.counts
  })
  const sources = ref<Partial<Record<DatabaseId, number>>>({
    ...kpiSnapshot.sources,
    ...cache.sources
  })
  const universities = ref<number | null>(cache.universities ?? kpiSnapshot.universities)
  const users = ref<number | null>(cache.users ?? kpiSnapshot.users)
  const universitiesStatus = ref<KpiStatus>('loading')
  const usersStatus = ref<KpiStatus>('loading')
  const countsSettled = ref(0)
  const countsFailed = ref(0)
  let fetched = false
  let homeFetched = false

  // Which KPIs already carry live values from earlier in this session — the
  // home page uses this to skip the first-load animations.
  const hydrated = {
    counts: Object.keys(cache.counts).length >= Object.keys(fetcherFor).length,
    universities: cache.universities != null,
    users: cache.users != null
  }

  function persist(): void {
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache))
    } catch {
      // The session cache only suppresses repeat animations; quota/private-mode
      // failures just mean the next load animates again.
    }
  }

  function fetch(): void {
    if (fetched) {
      return
    }
    fetched = true
    import('@/plugins/axios').then((apis) => {
      const fill = (
        fetchers: typeof fetcherFor,
        target: typeof counts,
        cached: KpiCache['counts'],
        tracked: boolean
      ): void =>
        Object.entries(fetchers).forEach(([id, fetcher]) => {
          fetcher(apis)
            .then((response) => {
              target.value = {
                ...target.value,
                [id]: response.data
              }
              cached[id as DatabaseId] = response.data
              persist()
            })
            .catch(() => {
              // counts are decorative; keep the seeded value on failure
              if (tracked) countsFailed.value++
            })
            .finally(() => {
              if (tracked) countsSettled.value++
            })
        })
      fill(fetcherFor, counts, cache.counts, true)
      fill(sourcesFetcherFor, sources, cache.sources, false)
    })
  }

  // The home page's remaining two live KPIs (distinct universities on the map,
  // analytics users). Fetched once per session, like the counts, so revisiting
  // the home page doesn't reset them to the snapshot and re-animate.
  function fetchHomeKpis(): void {
    if (homeFetched) {
      return
    }
    homeFetched = true
    import('@/plugins/axios').then(
      ({
        analyticsApi,
        bracesApi,
        columnsApi,
        connectionsApi,
        hssApi,
        materialsApi,
        residualsApi
      }) => {
        const latLngFields: (BraceField &
          ColumnField &
          ConnectionField &
          MaterialField &
          HSSColumnField)[] = ['latitude', 'longitude']
        Promise.all([
          bracesApi.getBracesCounts(latLngFields),
          columnsApi.getColumnsCounts(latLngFields),
          connectionsApi.getConnectionsCounts(latLngFields),
          materialsApi.getMaterialsCounts(latLngFields),
          residualsApi.getResidualStressesCounts(latLngFields),
          hssApi.getHssColumnsCounts(latLngFields)
        ])
          .then(
            (responses) =>
              new Set(responses.flatMap((response) => response.data.map((c) => c.names))).size
          )
          .then((count) => {
            universities.value = count
            universitiesStatus.value = 'live'
            cache.universities = count
            persist()
          })
          .catch(() => {
            universitiesStatus.value = 'stale'
          })

        analyticsApi
          .getUsers()
          .then((response) => response.data)
          .then((count) => {
            // The backend returns -1 when Google Analytics is unavailable
            // (e.g. no credentials in local dev) — keep the seeded value then,
            // marked stale so a broken analytics setup is visible on the tile.
            if (count >= 0) {
              users.value = count
              usersStatus.value = 'live'
              cache.users = count
              persist()
            } else {
              usersStatus.value = 'stale'
            }
          })
          .catch(() => {
            usersStatus.value = 'stale'
          })
      }
    )
  }

  // State of the 9 counts requests (sources don't gate any KPI), driving the
  // stale-while-revalidate bar under the home page's "tests digitized" number.
  const countsStatus = computed<KpiStatus>(() =>
    countsSettled.value < Object.keys(fetcherFor).length
      ? 'loading'
      : countsFailed.value > 0
      ? 'stale'
      : 'live'
  )

  const total = computed<number | undefined>(() => {
    const values = Object.values(counts.value)
    if (values.length < Object.keys(fetcherFor).length) {
      return undefined
    }
    return values.reduce((sum, value) => sum + (value ?? 0), 0)
  })

  return {
    counts,
    sources,
    total,
    countsStatus,
    universities,
    universitiesStatus,
    users,
    usersStatus,
    hydrated,
    fetch,
    fetchHomeKpis
  }
})
