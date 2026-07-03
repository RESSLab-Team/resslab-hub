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

/** Test counts per database, fetched once per session (sidebar, home tiles, dashboards). */
export const useCountsStore = defineStore('counts', () => {
  const counts = ref<Partial<Record<DatabaseId, number>>>({})
  let fetched = false

  function fetch(): void {
    if (fetched) {
      return
    }
    fetched = true
    import('@/plugins/axios').then((apis) => {
      Object.entries(fetcherFor).forEach(([id, fetcher]) => {
        fetcher(apis)
          .then((response) => {
            counts.value = {
              ...counts.value,
              [id]: response.data
            }
          })
          .catch(() => {
            // counts are decorative; leave the entry empty on failure
          })
      })
    })
  }

  const total = computed<number | undefined>(() => {
    const values = Object.values(counts.value)
    if (values.length < Object.keys(fetcherFor).length) {
      return undefined
    }
    return values.reduce((sum, value) => sum + (value ?? 0), 0)
  })

  return { counts, total, fetch }
})
