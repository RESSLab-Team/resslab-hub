<script setup lang="ts">
import { EccentricBracedFrameField, type EccentricBracedFrameModel } from '@/backend'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { useDataset } from '@/composables/useDataset'
import { EBF_KEY, fetchEbfs } from '@/components/ebf/data'
import { ebfApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: EccentricBracedFrameField.Investigator,
    titleKey: 'table.ebf.columns.experimentalProgram',
    type: 'text'
  },
  {
    value: EccentricBracedFrameField.SpecId,
    titleKey: 'table.ebf.columns.specimenDesignation',
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: EccentricBracedFrameField.Profile,
    titleKey: 'table.ebf.columns.linkCrossSection',
    type: 'text',
    cellVariant: 'mono'
  },
  {
    value: EccentricBracedFrameField.LinkLoc,
    titleKey: 'table.ebf.columns.linkLocation',
    type: 'text'
  },
  {
    value: EccentricBracedFrameField.E,
    titleKey: 'table.ebf.columns.linkLength',
    type: 'number'
  },
  {
    value: EccentricBracedFrameField.SgFlgLink,
    categoryColor: true,
    titleKey: 'table.ebf.columns.steelMaterial',
    type: 'text'
  }
]

const props = defineProps(tableProps)
const emit = defineEmits<TableEmits<EccentricBracedFrameModel>>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync, colorFor } =
  useDataset<EccentricBracedFrameModel>(EBF_KEY, fetchEbfs)
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
} = useTable<EccentricBracedFrameModel>(
  emit,
  'ebf',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'shear-link-angle',
      countKey: 'shear_link_angle_count',
      getCsv: (id) => ebfApi.getEccentricBracedFramesShearLinkAngleCsv(id)
    }
  ],
  getTotal,
  getPage,
  (ids) => ebfApi.getEccentricBracedFramesCsv(ids),
  (message) => notificationStore.notify(message),
  { countRowsSync, pageSync } // live crossfilter rows during a drag (see useTable)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:searches="searches"
    :color-for="colorFor"
    database-id="ebf"
    :columns="columns"
    :live-count="liveCount"
    :live-items="liveItems"
    :items="items"
    instant
    :loading="loading"
    prefix="ebf."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
  </simple-table>
</template>
