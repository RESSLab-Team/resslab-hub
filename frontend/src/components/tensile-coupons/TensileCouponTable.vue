<script setup lang="ts">
import { TensileCouponField, type TensileCouponModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { subscribeCrossfilter } from '@/composables/crossfilterBus'
import { useDataset } from '@/composables/useDataset'
import { TENSILE_COUPON_KEY, fetchTensileCoupons } from '@/components/tensile-coupons/data'
import { tensileCouponApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { onUnmounted, ref, toRef } from 'vue'

const columns: Column[] = [
  {
    value: TensileCouponField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: TensileCouponField.Id,
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: TensileCouponField.SteelGrade,
    type: 'text'
  },
  {
    value: TensileCouponField.Profile,
    type: 'text'
  },
  {
    value: TensileCouponField.SpecimenSource,
    type: 'text'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<TensileCouponModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync } = useDataset<TensileCouponModel>(
  TENSILE_COUPON_KEY,
  fetchTensileCoupons
)
const {
  clickRow,
  downloadFiles,
  items,
  loading,
  options,
  search,
  searches,
  totalCount,
  totalFilteredCount
} = useTable<TensileCouponModel>(
  emit,
  'tensile-coupon',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'stress-strain',
      countKey: 'stress_strain_count',
      getCsv: (id) => tensileCouponApi.getTensileCouponsStressStrainCsv(id)
    }
  ],
  getTotal,
  getPage,
  (ids) => tensileCouponApi.getTensileCouponsCsv(ids),
  (message) => notificationStore.notify(message)
)

// Live crossfilter: during a brush drag, stream the table's current page live from
// the in-memory dataset — the light-DOM virtualized body re-renders its visible
// rows in a few ms, so rows can track the drag frame-for-frame like the charts.
// `liveItems` replaces the body rows and `liveCount` drives the footer text; both
// are display-only (pagination still rides the committed totalFilteredCount, so no
// page-clamp refetch). Both clear on pointer-up, when the reactive commit settles.
const liveCount = ref<number>()
const liveItems = ref<TensileCouponModel[]>()
const unsubscribeCrossfilter = subscribeCrossfilter({
  onLive: (liveQuery) => {
    liveCount.value = countRowsSync(liveQuery)
    const opts = options.value
    liveItems.value = pageSync(
      liveQuery,
      opts?.sortBy?.map((sort) => sort.key),
      opts?.sortBy?.map((sort) => sort.order === 'desc'),
      opts?.page,
      opts?.itemsPerPage === -1 ? 1000 : opts?.itemsPerPage
    )
  },
  onSettle: () => {
    liveCount.value = undefined
    liveItems.value = undefined
  }
})
onUnmounted(unsubscribeCrossfilter)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:search="search"
    v-model:searches="searches"
    :columns="columns"
    hide-toolbar
    :live-count="liveCount"
    :live-items="liveItems"
    :items="items"
    instant
    :loading="loading"
    prefix="tensile_coupon."
    :query="query"
    :title="$t('table.tensile_coupon.title')"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  />
</template>
