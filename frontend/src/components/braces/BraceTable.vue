<script setup lang="ts">
import { BraceField, type BraceModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { useDataset } from '@/composables/useDataset'
import { BRACE_KEY, fetchBraces } from '@/components/braces/data'
import { bracesApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: BraceField.Investigator,
    type: 'text'
  },
  {
    value: BraceField.SpecimenId,
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: BraceField.CrossSectionSize,
    type: 'text',
    cellVariant: 'mono'
  },
  {
    value: BraceField.Steel,
    type: 'text'
  },
  {
    value: BraceField.KlR,
    title: 'kL/r<sub>y</sub>',

    type: 'number'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<BraceModel> {}
const emit = defineEmits<Emits>()

const notificationStore = useNotificationStore()
const { getTotal, getPage, countRowsSync, pageSync } = useDataset<BraceModel>(
  BRACE_KEY,
  fetchBraces
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
} = useTable<BraceModel>(
  emit,
  'brace',
  toRef(props, 'query'),
  toRef(props, 'search'),
  toRef(props, 'searches'),
  [
    {
      name: 'displacement',
      countKey: 'displacement_count',
      getCsv: (id) => bracesApi.getBracesDisplacementCsv(id)
    }
  ],
  getTotal,
  getPage,
  (ids) => bracesApi.getBracesCsv(ids),
  (message) => notificationStore.notify(message),
  { countRowsSync, pageSync } // live crossfilter rows during a drag (see useTable)
)
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
    prefix="brace."
    :query="query"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
    <template #title>
      {{ $t('table.brace.title') }}
      <info-tooltip>
        <p>{{ $t('table.brace.tooltip.intro') }}</p>
        {{ $t('table.brace.tooltip.howToUse') }}
        <ul>
          <li>{{ $t('table.brace.tooltip.bulletFilter') }}</li>
          <li>{{ $t('table.brace.tooltip.bulletClick') }}</li>
          <li>{{ $t('table.brace.tooltip.bulletDownload') }}</li>
          <li>{{ $t('table.brace.tooltip.bulletShare') }}</li>
        </ul>
      </info-tooltip>
    </template>
  </simple-table>
</template>
