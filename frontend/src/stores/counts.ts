import {
  bracesApi,
  columnsApi,
  connectionsApi,
  ductileFractureApi,
  ebfApi,
  hssApi,
  materialsApi,
  residualsApi,
  tensileCouponApi
} from '@/plugins/axios'
import type { DatabaseId } from '@/utils/navigation'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

const fetchers: Record<DatabaseId, () => Promise<{ data: number }>> = {
  connections: () => connectionsApi.getConnectionsDistinct(),
  columns: () => columnsApi.getColumnsDistinct(),
  braces: () => bracesApi.getBracesDistinct(),
  hss: () => hssApi.getHssColumnsDistinct(),
  ebf: () => ebfApi.getEccentricBracedFramesDistinct(),
  cyclic: () => materialsApi.getMaterialsDistinct(),
  tensile: () => tensileCouponApi.getTensileCouponsDistinct(),
  'ductile-fracture': () => ductileFractureApi.getDuctileFracturesDistinct(),
  residuals: () => residualsApi.getResidualStressesDistinct()
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
    Object.entries(fetchers).forEach(([id, fetcher]) => {
      fetcher()
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
  }

  const total = computed<number | undefined>(() => {
    const values = Object.values(counts.value)
    if (values.length < Object.keys(fetchers).length) {
      return undefined
    }
    return values.reduce((sum, value) => sum + (value ?? 0), 0)
  })

  return { counts, total, fetch }
})
