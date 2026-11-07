<script setup lang="ts">
import { ResidualStressField, type ResidualStressModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { useDataset } from '@/composables/useDataset'
import { RESIDUAL_KEY, fetchResiduals } from '@/components/residuals/data'
import { residualsApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { formatNumber } from '@/utils/formatter'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: ResidualStressField.ExperimentalProgram,
    type: 'text'
  },
  {
    value: ResidualStressField.Id,
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: ResidualStressField.Profile,
    type: 'text',
    cellVariant: 'mono'
  },
  {
    value: ResidualStressField.Steel,
    categoryColor: true,
    type: 'text'
  },
  {
    value: ResidualStressField.Tf,
    type: 'number',
    title: 't<sub>f</sub> [mm]'
  },
  {
    value: ResidualStressField.HOverB,
    title: 'h/b<sub>f</sub>',
    type: 'number',
    format: (value) => formatNumber(value, 2)
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<ResidualStressModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync, colorFor } = useDataset<ResidualStressModel>(
  RESIDUAL_KEY,
  fetchResiduals
)
const {
  clickRow,
  downloadFiles,
  items,
  liveCount,
  liveItems,
  loading,
  options,
  searches,
  totalCount,
  totalFilteredCount
} = useTable<ResidualStressModel>(
  emit,
  'residual',
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
  getTotal,
  getPage,
  (ids) => residualsApi.getResidualStressesCsv(ids),
  (message) => notificationStore.notify(message),
  { countRowsSync, pageSync } // live crossfilter rows during a drag (see useTable)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:searches="searches"
    :color-for="colorFor"
    database-id="residuals"
    :columns="columns"
    :live-count="liveCount"
    :live-items="liveItems"
    :items="items"
    instant
    :loading="loading"
    prefix="residual."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  />
</template>
