<script setup lang="ts">
import { EccentricBracedFrameField, type EccentricBracedFrameModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { ebfApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const columns: Column[] = [
  {
    value: EccentricBracedFrameField.Investigator,
    title: t('table.ebf.columns.experimentalProgram'),
    type: 'text'
  },
  {
    value: EccentricBracedFrameField.SpecId,
    title: t('table.ebf.columns.specimenDesignation'),
    type: 'text',
    cellVariant: 'strong'
  },
  {
    value: EccentricBracedFrameField.Profile,
    title: t('table.ebf.columns.linkCrossSection'),
    type: 'text',
    cellVariant: 'mono'
  },
  {
    value: EccentricBracedFrameField.LinkLoc,
    title: t('table.ebf.columns.linkLocation'),
    type: 'text'
  },
  {
    value: EccentricBracedFrameField.E,
    title: t('table.ebf.columns.linkLength'),
    type: 'number'
  },
  {
    value: EccentricBracedFrameField.SgFlgLink,
    title: t('table.ebf.columns.steelMaterial'),
    type: 'text'
  }
]

const props = defineProps(tableProps)
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends TableEmits<EccentricBracedFrameModel> {}
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
  () => ebfApi.getEccentricBracedFramesCounts(),
  (query, sortBy, sortDesc, page, size) =>
    ebfApi.getEccentricBracedFrames(query, sortBy, sortDesc, page, size),
  (ids) => ebfApi.getEccentricBracedFramesCsv(ids),
  (message) => notificationStore.notify(message)
)
</script>

<template>
  <simple-table
    v-model:options="options"
    v-model:search="search"
    v-model:searches="searches"
    :columns="columns"
    hide-toolbar
    :items="items"
    :loading="loading"
    prefix="ebf."
    :query="query"
    :title="$t('table.ebf.title')"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
    <template #title>
      {{ $t('table.ebf.title') }}
      <info-tooltip>
        <p>{{ $t('table.ebf.tooltip.intro') }}</p>
        {{ $t('table.ebf.tooltip.howToUse') }}
        <ul>
          <li>{{ $t('table.ebf.tooltip.bulletFilter') }}</li>
          <li>{{ $t('table.ebf.tooltip.bulletClick') }}</li>
          <li>{{ $t('table.ebf.tooltip.bulletDownload') }}</li>
          <li>{{ $t('table.ebf.tooltip.bulletShare') }}</li>
        </ul>
      </info-tooltip>
    </template>
  </simple-table>
</template>
