<script setup lang="ts">
import { EccentricBracedFrameField, type EccentricBracedFrameModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SimpleTable from '@/components/commons/SimpleTable.vue'
import { tableProps, useTable, type Column, type TableEmits } from '@/composables/table'
import { ebfApi } from '@/plugins/axios'
import { useNotificationStore } from '@/stores/notification'
import { toRef } from 'vue'

const columns: Column[] = [
  {
    value: EccentricBracedFrameField.Investigator,
    title: 'Experimental Program',
    type: 'text'
  },
  {
    value: EccentricBracedFrameField.SpecId,
    title: 'Specimen Designation',
    type: 'text'
  },
  {
    value: EccentricBracedFrameField.Profile,
    title: 'Link cross-section',
    type: 'text'
  },
  {
    value: EccentricBracedFrameField.LinkLoc,
    title: 'Link location',
    type: 'text'
  },
  {
    value: EccentricBracedFrameField.E,
    title: 'Link length [mm]',
    type: 'number'
  },
  {
    value: EccentricBracedFrameField.SgFlgLink,
    title: 'Steel material [MPa]',
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
    :items="items"
    :loading="loading"
    prefix="ebf."
    :query="query"
    title="Eccentric Braced Frames"
    :total-count="totalCount"
    :total-filtered-count="totalFilteredCount"
    @click:row="clickRow"
    @download="downloadFiles"
  >
    <template #title>
      Eccentric Braced Frames
      <info-tooltip>
        <p>
          The Eccentric Braced Frames Database presents data from early 1977s on EBF under reversed
          cyclic and monotonic loading. The primary data involve the deduced shear-link angle of the
          EBF link.
        </p>
        How to use?
        <ul>
          <li>
            Filter the table by making selections in the various plots around the table, or by using
            the filters and dropdowns above the table headers.
          </li>
          <li>Click on a row to see the data of a single test.</li>
          <li>
            Download specific tests results by selecting the test (left-most column) and click
            "Download" below.
          </li>
          <li>
            Share specific tests results by selecting the test (left-most column) and click "Share"
            below.
          </li>
        </ul>
      </info-tooltip>
    </template>
  </simple-table>
</template>
