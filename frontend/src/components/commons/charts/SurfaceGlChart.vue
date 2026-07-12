<script setup lang="ts">
import { updateOptions } from '@/components/commons/charts/utils'
import type { EChartsGlOption } from '@/utils/echarts-gl'
import { SurfaceChart } from 'echarts-gl/charts'
import { Grid3DComponent } from 'echarts-gl/components'
import { TooltipComponent } from 'echarts/components'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { merge, round } from 'lodash'
import { computed } from 'vue'
import VChart from 'vue-echarts'

use([CanvasRenderer, SurfaceChart, Grid3DComponent, TooltipComponent])

const props = withDefaults(
  defineProps<{
    option: EChartsGlOption
    aspectRatio?: number
    /** Fill the parent's height instead of sizing by aspect ratio
        (Rail+Stage tool layout — the block sets an explicit height). */
    fill?: boolean
  }>(),
  {
    aspectRatio: 1,
    fill: false
  }
)

const axisLabelMaxDigits = 2

const actualOption = computed<EChartsGlOption>(() => {
  const defaultOption: EChartsGlOption = {
    tooltip: {
      confine: true
    },
    grid3D: {
      viewControl: {
        distance: 260
      }
    },
    xAxis3D: {
      min: 'dataMin',
      max: 'dataMax',
      axisLabel: {
        formatter: (value) => `${round(value, axisLabelMaxDigits)}`
      }
    },
    yAxis3D: {
      min: 'dataMin',
      max: 'dataMax',
      axisLabel: {
        formatter: (value) => `${round(value, axisLabelMaxDigits)}`
      }
    },
    zAxis3D: {
      min: 'dataMin',
      max: 'dataMax',
      axisLabel: {
        formatter: (value) => `${round(value, axisLabelMaxDigits)}`
      }
    }
  }
  return merge(defaultOption, props.option)
})
</script>

<template>
  <div v-if="fill" class="sgl-fill">
    <v-chart autoresize :option="actualOption" :update-options="updateOptions" />
  </div>
  <v-responsive v-else :aspect-ratio="aspectRatio">
    <v-chart autoresize :option="actualOption" :update-options="updateOptions" />
  </v-responsive>
</template>

<style scoped>
.sgl-fill {
  width: 100%;
  height: 100%;
  min-height: 0;
}
.sgl-fill > :deep(.echarts) {
  width: 100%;
  height: 100%;
}
</style>
