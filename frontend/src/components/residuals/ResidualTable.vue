<script setup lang="ts">
import { ResidualStressField, type ResidualStressModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { residualsApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: ResidualStressField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: ResidualStressField.Id,
    type: 'text'
  },
  {
    value: ResidualStressField.Profile,
    type: 'text'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<ResidualStressModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
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
} = useTable<ResidualStressModel>(
  emit,
  'material',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'distribution-f1',
      countKey: 'distribution_F1_count',
      getCsv: (id) => residualsApi.getResidualStressesDistributionF1Csv(id)
    },
    {
      name: 'distribution-f2',
      countKey: 'distribution_F2_count',
      getCsv: (id) => residualsApi.getResidualStressesDistributionF2Csv(id)
    },
    {
      name: 'distribution-w1',
      countKey: 'distribution_W1_count',
      getCsv: (id) => residualsApi.getResidualStressesDistributionW1Csv(id)
    }
  ],
  () => residualsApi.getResidualStressesCounts(),
  (query, sortBy, sortDesc, page, size) =>
    residualsApi.getResidualStresses(query, sortBy, sortDesc, page, size),
  (ids) => residualsApi.getResidualStressesCsv(ids),
  (message) => notificationStore.notify(message)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:search="search"
    v-model:searches="searches"
    :columns="columns"
    :items="items"
    :loading="loading"
    prefix="residual."
    :query="query"
    title="Residual Stress"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  />
</template>
