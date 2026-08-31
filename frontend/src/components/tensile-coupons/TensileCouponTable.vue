<script setup lang="ts">
import { TensileCouponField, type TensileCouponModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { useDataset } from '@/composables/useDataset'
import { TENSILE_COUPON_KEY, fetchTensileCoupons } from '@/components/tensile-coupons/data'
import { tensileCouponApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'

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
    categoryColor: true,
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
const { getTotal, getPage, countRowsSync, pageSync, colorFor } = useDataset<TensileCouponModel>(
  TENSILE_COUPON_KEY,
  fetchTensileCoupons
)
const {
  clickRow,
  downloadFiles,
  items,
  liveCount,
  liveItems,
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
  (message) => notificationStore.notify(message),
  { countRowsSync, pageSync } // live crossfilter rows during a drag (see useTable)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:search="search"
    v-model:searches="searches"
    :color-for="colorFor"
    database-id="tensile"
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
