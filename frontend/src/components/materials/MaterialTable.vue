<script setup lang="ts">
import { MaterialField, type MaterialModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { subscribeCrossfilter } from '@/composables/crossfilterBus'
import { useDataset } from '@/composables/useDataset'
import { MATERIAL_KEY, fetchMaterials } from '@/components/materials/data'
import { materialsApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { onUnmounted, ref, toRef } from 'vue'

const columns: Column[] = [
  {
    value: MaterialField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: MaterialField.Id,
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: MaterialField.Type,
    type: 'text'
  },
  {
    value: MaterialField.Profile,
    type: 'text'
  },
  {
    value: MaterialField.Source,
    type: 'text'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<MaterialModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync } = useDataset<MaterialModel>(
  MATERIAL_KEY,
  fetchMaterials
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
} = useTable<MaterialModel>(
  emit,
  'material',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'stress-strain',
      countKey: 'stress_strain_count',
      getCsv: (id) => materialsApi.getMaterialsStressStrainCsv(id)
    }
  ],
  getTotal,
  getPage,
  (ids) => materialsApi.getMaterialsCsv(ids),
  (message) => notificationStore.notify(message)
)

// Live crossfilter: during a brush drag, stream the table's current page live from
// the in-memory dataset — the light-DOM virtualized body re-renders its visible
// rows in a few ms, so rows can track the drag frame-for-frame like the charts.
// `liveItems` replaces the body rows and `liveCount` drives the footer text; both
// are display-only (pagination still rides the committed totalFilteredCount, so no
// page-clamp refetch). Both clear on pointer-up, when the reactive commit settles.
const liveCount = ref<number>()
const liveItems = ref<MaterialModel[]>()
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
    prefix="material."
    :query="query"
    :title="$t('table.material.title')"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  />
</template>
