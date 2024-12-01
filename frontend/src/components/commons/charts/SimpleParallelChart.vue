<script setup lang="ts">
import { initOptions, updateOptions } from '@/components/commons/charts/utils'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import type { ParallelField } from '@/composables/chart'
import i18n from '@/plugins/i18n'
import type { Value } from '@/utils/common'
import type { VerticalAlign, ZRFontWeight } from '@/utils/echarts'
import { primaryColor, type Color } from '@/utils/vuetify'
import { mdiFilterVariant, mdiCancel } from '@mdi/js'
import type { EChartsOption } from 'echarts'
import { ParallelChart } from 'echarts/charts'
import { BrushComponent, ToolboxComponent } from 'echarts/components'
import { use, type ECharts } from 'echarts/core'
import { SVGRenderer } from 'echarts/renderers'
import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { chain, merge, zip } from 'lodash'
import { computed, ref, unref } from 'vue'
import VChart from 'vue-echarts'
import ResetChartButton from '@/components/commons/ResetChartButton.vue'

use([SVGRenderer, ParallelChart, BrushComponent, ToolboxComponent])

// TODO add genericity https://github.com/vuejs/rfcs/discussions/436
type F = string
const props = withDefaults(
  defineProps<{
    color?: Color
    data: (number | string)[][]
    fields?: ParallelField<F>[]
    ids: string[]
    labelPrefix?: string
    requestFields: F[]
    isFiltered: boolean
  }>(),
  {
    color: () => primaryColor,
    data: () => [],
    fields: () => [],
    counts: () => [],
    ids: () => [],
    labelPrefix: '',
    requestFields: () => []
  }
)
const emit = defineEmits<{
  (e: 'change:searches', value?: Value): void
}>()

const chart = ref<ECharts>()
const selectedIds = ref<string[]>([])

const transposedData = computed<(string | number)[][]>(
  () => zip(...props.data) as (string | number)[][]
)
const option = computed<EChartsOption>(() => ({
  parallel: {
    left: 60,
    top: 40,
    right: 120,
    bottom: 8,
    axisExpendable: true
  },
  parallelAxis: props.fields.map((field, index) => {
    const id: string =
      typeof field.id === 'string' ? field.id : `${field.id.dividend}/${field.id.divisor}`
    const name = field.name ?? i18n.global.t(props.labelPrefix + id).toString()
    const values = getValues(field)
    const option = {
      id: id,
      dim: index,
      name: name,
      nameTextStyle: {
        fontWeight: 'bold' as ZRFontWeight,
        verticalAlign: 'middle' as VerticalAlign
      },
      nameGap: 20
    }
    if (values) {
      const type = typeof values.find((v) => v != null)
      if (type === 'number') {
        return merge(option, {
          type: 'value',
          scale: true
        })
      } else {
        const sortedValues = chain(values).uniq().sort().value()
        return merge(option, {
          nameLocation: 'start',
          inverse: true,
          type: 'category',
          axisTick: {
            alignWithLabel: true
          },
          data: sortedValues
        })
      }
    } else {
      return option
    }
  }),
  series: {
    type: 'parallel',

    data: props.data.map((d) =>
      props.fields.map((f) => {
        const requestFieldsValue = props.requestFields
        if (typeof f.id === 'string') {
          const value = d[requestFieldsValue.indexOf(f.id)]
          if (f.mapping && typeof value === 'string') return f.mapping.get(value) || value
          else return value
        } else {
          return (
            (d[requestFieldsValue.indexOf(f.id.dividend)] as number) /
            (d[requestFieldsValue.indexOf(f.id.divisor)] as number)
          )
        }
      })
    ),
    emphasis: {
      focus: 'series',
      lineStyle: {
        width: 6
      }
    }
  },
  color: props.color.base
}))

function getValues(field: ParallelField): (string | number)[] {
  const transposedDataValue = unref(transposedData)
  const requestFieldsValue = props.requestFields
  if (typeof field.id === 'string') {
    const values = transposedDataValue[requestFieldsValue.indexOf(field.id)]
    if (field.mapping && values)
      return values.map((d) =>
        typeof d == 'string' ? (field.mapping as Map<string, string>).get(d) || d : d
      )
    else return values
  } else {
    return zip(
      transposedDataValue[requestFieldsValue.indexOf(field.id.dividend)],
      transposedDataValue[requestFieldsValue.indexOf(field.id.divisor)]
    )
      .map((v) => v as [number, number])
      .map((v) => v[0] / v[1])
  }
}
function onClick(params: CallbackDataParams): void {
  emit('change:searches', props.ids[params.dataIndex])
}
function onBrush(): void {
  // @ts-ignore need to ignore because now the only way to retrieve selected indexes from parallel chart is to use private API
  // see https://github.com/apache/echarts/blob/d08664fffe9e6cb4851519e50cf8c7c42f0427ae/src/chart/parallel/ParallelSeries.ts#L105
  // or https://echarts.apache.org/en/api.html#events.axisareaselected
  const selectedIndexes: number[] = chart.value?.chart
    .getModel()
    .getSeries()[0]
    .getRawIndicesByActiveState('active')

  if (selectedIndexes.length > 0) {
    selectedIds.value = selectedIndexes.map((index) => props.ids[index])
  }
}

function onApply(): void {
  emit('change:searches', selectedIds.value.join(','))
  clear()
}
function clear(): void {
  selectedIds.value = []
  chart.value?.clear()
}

function restore(): void {
  chart.value?.dispatchAction({ type: 'restore' })
  selectedIds.value = []
}

function reset(): void {
  emit('change:searches', undefined)
  clear()
}
</script>

<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between">
      <div>
        <slot name="title">
          Parallel View of all Tests
          <info-tooltip>
            <p>
              In this parallel coordinate plots, you can view all available tests in the database,
              ordered according to key variables. Each line represents a single test.
            </p>
            How to use?
            <ul>
              <li>Filter a subset of the data by selecting values on the vertical axis directly</li>
              <li>Select a specific test by clicking on the respective line.</li>
            </ul>
          </info-tooltip>
        </slot>
      </div>

      <reset-chart-button
        :field="requestFields"
        :is-filtered="isFiltered"
        @change:searches="reset"
      />
    </v-card-title>
    <v-responsive aspect-ratio="4" min-height="275">
      <v-chart
        ref="chart"
        autoresize
        :init-options="initOptions"
        :option="option"
        :update-options="updateOptions"
        @click="onClick"
        @axisareaselected="onBrush"
      />
    </v-responsive>
    <v-card-actions>
      <v-btn
        color="primary"
        :disabled="selectedIds.length === 0"
        :prepend-icon="mdiFilterVariant"
        @click="onApply"
      >
        Apply selection ({{ selectedIds.length }})
      </v-btn>
      <v-btn
        color="primary"
        :disabled="selectedIds.length === 0"
        :prepend-icon="mdiCancel"
        @click="restore"
      >
        Clear selection
      </v-btn>
    </v-card-actions>
  </v-card>
</template>
