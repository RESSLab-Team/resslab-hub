<script setup lang="ts">
import { initOptions, updateOptions } from '@/components/commons/charts/utils'
import type { Count } from '@/composables/chart'
import i18n from '@/plugins/i18n'
import type { Value } from '@/utils/common'
import { getColorPalette, primaryColor, type Color } from '@/utils/vuetify'
import type { EChartsOption } from 'echarts'
import { TreemapChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { computed } from 'vue'
import VChart from 'vue-echarts'
import ResetChartButton from '@/components/commons/ResetChartButton.vue'

use([SVGRenderer, TreemapChart, TooltipComponent])

const props = withDefaults(
  defineProps<{
    color?: Color
    counts?: Count[]
    field: string
    labelPrefix?: string
    flat?: boolean
    mapping?: Map<string, string>
    showReset?: boolean
  }>(),
  {
    color: () => primaryColor,
    counts: () => [],
    flat: false,
    showReset: true,
    mapping: () => new Map<string, string>(),
    labelPrefix: ''
  }
)
const emit = defineEmits<{
  (e: 'change:searches', key: string, value?: Value): void
  (e: 'mouseover', value: CallbackDataParams): void
  (e: 'mouseout'): void
}>()

const option = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: 'item',
    confine: true
  },
  series: [
    {
      type: 'treemap',
      id: props.field,
      name: i18n.global.t(props.labelPrefix + props.field).toString(),
      left: 0,
      top: 0,
      right: 0,
      bottom: 0,
      data: props.counts.map((count) => {
        const label = props.mapping.get(count.name) ?? count.name
        return {
          name: label,
          value: count.value
        }
      }),
      breadcrumb: {
        show: false
      },
      roam: false
    }
  ],
  color: getColorPalette(props.color, props.counts.length)
}))

function click(params: CallbackDataParams): void {
  if (params.seriesId) {
    emit('change:searches', params.seriesId, params.name)
  }
}

function changeSearches(key: string, value?: Value) {
  emit('change:searches', key, value)
}
</script>

<template>
  <v-card :flat="flat">
    <v-card-title class="d-flex justify-space-between">
      <slot name="title"> </slot>
      <reset-chart-button
        v-if="showReset"
        :field="field"
        :is-filtered="counts.length === 1"
        @change:searches="changeSearches"
      />
    </v-card-title>
    <v-card-text :class="[flat ? 'pa-0' : '']">
      <v-responsive min-height="100">
        <v-chart
          autoresize
          :init-options="initOptions"
          :option="option"
          :update-options="updateOptions"
          @click="click"
          @mouseover="emit('mouseover', $event)"
          @mouseout="emit('mouseout')"
        />
      </v-responsive>
      <slot></slot>
    </v-card-text>
  </v-card>
</template>
