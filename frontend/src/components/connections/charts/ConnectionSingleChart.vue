<script setup lang="ts">
import { ConnectionField } from '@/backend'
import SingleChart from '@/components/commons/charts/SingleChart.vue'
import { singleChartProps, useSingleChart, type ChartEmits } from '@/composables/chart'
import { connectionsApi } from '@/plugins/axios'
import { publicPath } from '@/utils/common'
import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { ref, toRef } from 'vue'

const props = defineProps(singleChartProps<ConnectionField>())
// eslint-disable-next-line @typescript-eslint/no-empty-interface
interface Emits extends ChartEmits {}
const emit = defineEmits<Emits>()

const { counts, changeSearches } = useSingleChart<ConnectionField>(
  emit,
  props.field,
  toRef(props, 'query'),
  (fields, query) => connectionsApi.getConnectionsCounts(fields, query)
)

const imageUrl = ref<string>()

function mouseover(params: CallbackDataParams): void {
  if (props.field === ConnectionField.ConnectionType) {
    const name: string = params.name.toLowerCase()
    imageUrl.value = publicPath + 'img/connection-type/' + name + '.svg'
  }
}

function mouseout(): void {
  imageUrl.value = undefined
}
</script>

<template>
  <single-chart
    :color="color"
    :counts="counts"
    :flat="flat"
    :field="field"
    label-prefix="connection."
    @change:searches="changeSearches"
    @mouseover="mouseover"
    @mouseout="mouseout"
  >
    <template #default>
      <v-img v-if="imageUrl" aspect-ratio="3" :src="imageUrl" min-height="120" />
    </template>
    <template #title> <slot name="title"></slot> </template>
  </single-chart>
</template>
