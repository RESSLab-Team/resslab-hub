<script setup lang="ts">
import { updateOptions } from '@/components/commons/charts/utils'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import { isDivision, type ParallelField } from '@/composables/chart'
import i18n from '@/plugins/i18n'
import type { Value } from '@/utils/common'
import type { VerticalAlign, ZRFontWeight } from '@/utils/echarts'
import { primaryColor, type Color } from '@/utils/vuetify'
import { mdiFilterVariant, mdiCancel } from '@mdi/js'
import type { EChartsOption } from 'echarts'
import { ParallelChart } from 'echarts/charts'
import { BrushComponent, ToolboxComponent } from 'echarts/components'
import { use, type ECharts } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import type { CallbackDataParams } from 'echarts/types/dist/shared'
import { chain, merge, zip } from 'lodash'
import { computed, ref, unref } from 'vue'
import VChart from 'vue-echarts'
import ResetChartButton from '@/components/commons/ResetChartButton.vue'

// Canvas (not the app-wide SVG) for this one chart: it draws one polyline per
// filtered record, so element count scales with the result set — canvas keeps
// that cheap where SVG's DOM cost would not. devicePixelRatio keeps it crisp.
use([CanvasRenderer, ParallelChart, BrushComponent, ToolboxComponent])
const canvasInitOptions = { renderer: 'canvas' as const }

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

// Position of each request field, precomputed once — the data projection and
// getValues below run per row × field, so an O(1) lookup replaces repeated
// requestFields.indexOf(...) (was O(rows × fields × requestFields) per recompute).
const fieldIndex = computed<Map<F, number>>(
  () => new Map(props.requestFields.map((f, i) => [f, i]))
)

const chartHeight = computed(() => {
  // Find the field with the most categories
  const maxCategories = Math.max(
    ...props.fields.map((field) => {
      const values = getValues(field)?.filter((d) => d != null && d !== undefined)
      if (!values || typeof values[0] === 'number') return 0
      return new Set(values).size
    })
  )

  // Base height + additional height per category
  const baseHeight = 300
  const heightPerCategory = 30
  const additionalHeight = Math.max(0, maxCategories - 10) * heightPerCategory

  return baseHeight + additionalHeight
})

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
      typeof field.id === 'string'
        ? field.id
        : isDivision(field.id)
        ? `${field.id.dividend}/${field.id.divisor}`
        : field.id.key
    const name = field.name ?? i18n.global.t(props.labelPrefix + id).toString()
    const values = getValues(field)
    const option = {
      id: id,
      dim: index,
      name: name,
      nameTextStyle: {
        color: '#6e6e73',
        fontWeight: 'normal' as ZRFontWeight,
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
        const sortedValues = field.sortValues || chain(values).uniq().sort().value()
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
        const idx = unref(fieldIndex)
        if (typeof f.id === 'string') {
          const value = d[idx.get(f.id) ?? -1]
          if (f.mapping && typeof value === 'string') return f.mapping.get(value) || value
          else return value
        } else if (isDivision(f.id)) {
          return (
            (d[idx.get(f.id.dividend) ?? -1] as number) / (d[idx.get(f.id.divisor) ?? -1] as number)
          )
        } else {
          const values = f.id.fields.map((field) => {
            const v = d[idx.get(field) ?? -1]
            return v == null ? null : (v as number)
          })
          return f.id.compute(values) as number
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
  const idx = unref(fieldIndex)
  if (typeof field.id === 'string') {
    const values = transposedDataValue[idx.get(field.id) ?? -1]
    if (field.mapping && values)
      return values.map((d) =>
        typeof d == 'string' ? (field.mapping as Map<string, string>).get(d) || d : d
      )
    else return values
  } else if (isDivision(field.id)) {
    return zip(
      transposedDataValue[idx.get(field.id.dividend) ?? -1],
      transposedDataValue[idx.get(field.id.divisor) ?? -1]
    )
      .map((v) => v as [number, number])
      .map((v) => v[0] / v[1])
  } else {
    const computed = field.id
    const columns = computed.fields.map((f) => transposedDataValue[idx.get(f) ?? -1] ?? [])
    const rowCount = columns[0]?.length ?? 0
    const values: (number | null)[] = []
    for (let i = 0; i < rowCount; i++) {
      const rowValues = columns.map((col) => {
        const v = col[i]
        return v == null ? null : (v as number)
      })
      values.push(computed.compute(rowValues))
    }
    return values as (string | number)[]
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
  <v-card height="100%">
    <v-card-title class="d-flex justify-space-between">
      <div>
        <slot name="title">
          {{ $t('commons.parallel_view_title') }}
          <info-tooltip>
            <p>{{ $t('commons.parallel_view_intro') }}</p>
            {{ $t('commons.parallel_view_how_to') }}
            <ul>
              <li>{{ $t('commons.parallel_view_bullet_filter') }}</li>
              <li>{{ $t('commons.parallel_view_bullet_select') }}</li>
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
    <div class="chart-container" :style="`height: ${chartHeight}px;`">
      <v-chart
        ref="chart"
        autoresize
        :init-options="canvasInitOptions"
        :option="option"
        :update-options="updateOptions"
        @click="onClick"
        @axisareaselected="onBrush"
      />
    </div>
    <v-card-actions>
      <v-btn
        color="primary"
        :disabled="selectedIds.length === 0"
        :prepend-icon="mdiFilterVariant"
        @click="onApply"
      >
        {{ $t('commons.apply_selection', { n: selectedIds.length }) }}
      </v-btn>
      <v-btn
        color="primary"
        :disabled="selectedIds.length === 0"
        :prepend-icon="mdiCancel"
        @click="restore"
      >
        {{ $t('commons.clear_selection') }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<style scoped>
/* Chart title → card-title role (matches ChartCell's .chart-head h5), so a
   standalone chart card reads the same as a dashboard-strip chart. */
:deep(.v-card-title) {
  font-size: var(--title-card-size);
  font-weight: var(--title-card-weight);
  letter-spacing: var(--title-card-tracking);
  line-height: 1.3;
}
</style>
