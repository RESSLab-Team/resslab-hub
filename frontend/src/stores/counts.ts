import type { DatabaseId } from '@/utils/navigation'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

// The API client is imported lazily inside fetch(): this store is reachable
// from the entry bundle (App → sidebar badges), and a static import here would
// pull axios + the whole generated client (~1/5 of the old entry chunk) into
// the first paint for what is a decorative, post-mount fetch.
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

/** Test and source counts per database, fetched once per session (sidebar, home tiles). */
export const useCountsStore = defineStore('counts', () => {
  const counts = ref<Partial<Record<DatabaseId, number>>>({})
  const sources = ref<Partial<Record<DatabaseId, number>>>({})
  let fetched = false

  function fetch(): void {
    if (fetched) {
      return
    }
    fetched = true
    import('@/plugins/axios').then((apis) => {
      const fill = (fetchers: typeof fetcherFor, target: typeof counts): void =>
        Object.entries(fetchers).forEach(([id, fetcher]) => {
          fetcher(apis)
            .then((response) => {
              target.value = {
                ...target.value,
                [id]: response.data
              }
            })
            .catch(() => {
              // counts are decorative; leave the entry empty on failure
            })
        })
      fill(fetcherFor, counts)
      fill(sourcesFetcherFor, sources)
    })
  }

  const total = computed<number | undefined>(() => {
    const values = Object.values(counts.value)
    if (values.length < Object.keys(fetcherFor).length) {
      return undefined
    }
    return values.reduce((sum, value) => sum + (value ?? 0), 0)
  })

  return { counts, sources, total, fetch }
})
