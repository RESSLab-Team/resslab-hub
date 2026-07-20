<script setup lang="ts">
// Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/fragility_curves_steel_columns
import LegendChart from '@/components/commons/charts/LegendChart.vue'
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import ToolShell from '@/components/commons/ToolShell.vue'
import ToolSlider from '@/components/commons/tools/ToolSlider.vue'
import type { EChartsGlOption } from '@/utils/echarts-gl'
import { univariateOption } from '@/utils/fragility'
import { subscripts } from '@/utils/unicode'
import { getColorMap } from '@/utils/vuetify'
import type { EChartsOption, SeriesOption } from 'echarts'
import { range } from 'lodash'
import { computed, defineAsyncComponent, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

// Lazy-load the 3D surface so the heavy echarts-gl (WebGL) bundle only loads
// when a 3D plot is actually rendered.
const SurfaceGlChart = defineAsyncComponent(
  () => import('@/components/commons/charts/SurfaceGlChart.vue')
)

const parameters: {
  key: keyof Variables
  label: string
  min: number
  max: number
  unit?: string
}[] = [
  {
    key: 'hTw',
    label: 'h / tw',
    min: 5,
    max: 60
  },
  {
    key: 'pPyn',
    label: 'Pg / Pyn',
    min: 0,
    max: 1
  }
]
const alphas: number[] = [5.515, 10.753, 14.664, 16.659]
const maxSdr = 11.01
const sdr = range(0, maxSdr, 0.01)

interface Variables {
  hTw: number
  pPyn: number
}
const variables = reactive<Variables>({
  hTw: 40,
  pPyn: 0.2
})

const alphaColorPalette = getColorMap(alphas.length)
const legendItems = ref([
  ...alphas.map((_, index) => ({
    id: `DS${index + 1}`,
    label: `DS${index + 1}`,
    indexToFilter: index,
    color: alphaColorPalette[index],
    icon: 'mdi-rectangle',
    selected: true
  })),
  {
    id: 'univariate',
    label: t('tools.column_fragility.legend_univariate'),
    color: 'black',
    icon: 'mdi-rectangle',
    selected: true,
    indexToFilter: -1
  },
  {
    id: 'multivariate',
    label: t('tools.column_fragility.legend_multivariate'),
    color: 'black',
    icon: 'mdi-dots-horizontal',
    selected: true,
    indexToFilter: -1
  }
])
const indexSelected = computed<number[]>(() =>
  legendItems.value.filter((d) => d.indexToFilter >= 0 && d.selected).map((d) => d.indexToFilter)
)
const univariateSelected = computed<boolean>(
  () => legendItems.value.find((d) => d.id === 'univariate')?.selected || false
)
const multivariateSelected = computed<boolean>(
  () => legendItems.value.find((d) => d.id === 'multivariate')?.selected || false
)
const variateOption = computed<EChartsOption>(() => {
  const series: SeriesOption[] = []
  if (univariateSelected.value) {
    const option = univariateOption(
      [
        {
          median: 0.507,
          beta: 0.425
        },
        {
          median: 1.368,
          beta: 0.552
        },
        {
          median: 2.292,
          beta: 0.491
        },
        {
          median: 3.502,
          beta: 0.321
        }
      ],
      maxSdr,
      `${t('tools.column_fragility.legend_univariate')} `
    )
    const selectedUnivariateSeries: SeriesOption[] = (option.series as SeriesOption[]).filter(
      (_, index) => indexSelected.value.includes(index)
    )
    if (selectedUnivariateSeries.length > 0) {
      series.push(...selectedUnivariateSeries)
    }
  }
  if (multivariateSelected.value) {
    const option = {
      xAxis: {
        name: 'SDR'
      },
      yAxis: {
        name: 'P(DS≥ds)'
      },
      series: alphas.map((alpha, index) => ({
        type: 'line',
        name: `${t('tools.column_fragility.legend_multivariate')} P(DS≥ds${
          subscripts[(index + 1).toString()]
        })`,
        showSymbol: false,
        animation: false,
        itemStyle: {
          color: alphaColorPalette[index]
        },
        lineStyle: {
          color: alphaColorPalette[index],
          type: 'dotted'
        },
        data: sdr.map((item) => [item, surface(variables.hTw, item, alpha, variables.pPyn)])
      }))
    }
    const selectedMultivariateSeries: SeriesOption[] = (option.series as SeriesOption[]).filter(
      (_, index) => indexSelected.value.includes(index)
    )
    if (selectedMultivariateSeries.length > 0) {
      series.push(...selectedMultivariateSeries)
    }
  }
  return {
    xAxis: {
      name: 'SDR'
    },
    yAxis: {
      name: 'P(DS)'
    },
    legend: {
      show: false
    },
    series
  } as EChartsOption
})
const surfaceOptions = computed<EChartsGlOption[]>(() =>
  alphas.map((alpha, index) =>
    getSurfaceOption(
      (index + 1).toString(),
      alpha,
      variables.hTw,
      variables.pPyn,
      alphaColorPalette[index]
    )
  )
)

function getSurfaceOption(
  name: string,
  alpha: number,
  hTw: number,
  pPyn: number,
  color: string
): EChartsGlOption {
  const yMin = 0
  const yMax = 7
  const zMin = 0
  const zMax = 1
  return {
    xAxis3D: {
      name: 'h/tw',
      nameTextStyle: {
        fontSize: 14
      }
    },
    yAxis3D: {
      name: 'SDR [% rad]',
      nameTextStyle: {
        fontSize: 14
      }
    },
    zAxis3D: {
      name: `P(DS${name})`,
      nameTextStyle: {
        fontSize: 14
      }
    },
    series: [
      {
        type: 'surface',
        name: '',
        wireframe: {
          show: false
        },
        equation: {
          x: {
            min: 0,
            max: 60,
            step: 1
          },
          y: {
            min: yMin,
            max: yMax,
            step: 0.1
          },
          z: (x: number, y: number) => {
            return surface(x, y, alpha, pPyn)
          }
        },
        itemStyle: {
          color
        }
      },
      {
        type: 'surface',
        name: '',
        itemStyle: {
          color: 'black',
          opacity: 0.5
        },
        data: [
          [hTw, yMin, zMin],
          [hTw, yMin, zMax],
          [hTw, yMax, zMin],
          [hTw, yMax, zMax]
        ],
        silent: true,
        dataShape: [2, 2]
      }
    ]
  }
}

function surface(hTw: number, sdr: number, alpha: number, pPyn: number): number {
  const betaHtw = -0.15
  const betaPpy = -11.081
  const betaSdr = -5.708
  const y = alpha + betaHtw * hTw + betaPpy * pPyn + betaSdr * Math.log(sdr)
  return 1 - Math.exp(y) / (1 + Math.exp(y))
}
</script>

<template>
  <tool-shell
    :eyebrow="$t('tools.common.fragility_eyebrow')"
    :title="$t('tools.column_fragility.title')"
    layout="parambar"
  >
    <template #intro>
      <i18n-t keypath="tools.column_fragility.intro" tag="span" scope="global">
        <template #reference>
          <a
            target="_blank"
            href="https://journals.sagepub.com/doi/abs/10.1193/122017EQS260M?journalCode=eqsa"
            >{{ $t('tools.column_fragility.intro_reference') }}</a
          >
        </template>
      </i18n-t>
    </template>

    <template #parambar>
      <div v-for="item in parameters" :key="item.key" class="pb-group pb-slider">
        <tool-slider
          v-model="variables[item.key]"
          :label="item.label"
          :max="item.max"
          :min="item.min"
          :unit="item.unit"
        />
      </div>
    </template>

    <template #stage>
      <div class="st-chart">
        <div class="chart-cap">
          <div class="chart-cap-t">
            <h2 class="chart-h">{{ $t('tools.column_fragility.fragility_curves') }}</h2>
            <p class="chart-sub">{{ $t('tools.column_fragility.fragility_curves_sub') }}</p>
          </div>
        </div>
        <div class="curve-row">
          <div class="tchart h-chart">
            <unit-chart fill :option="variateOption" x-unit="rad" />
          </div>
          <legend-chart v-model="legendItems" :separators-index="[4]" />
        </div>
      </div>

      <div class="e-surfaces-head">
        <h3 class="chart-h">{{ $t('tools.column_fragility.surface_fragility_curves') }}</h3>
        <p class="chart-sub">{{ $t('tools.column_fragility.surface_fragility_curves_sub') }}</p>
      </div>
      <div class="st-surfaces">
        <div v-for="(item, index) in surfaceOptions" :key="index" class="tchart h-surface">
          <surface-gl-chart fill :option="item" />
        </div>
      </div>
    </template>
  </tool-shell>
</template>
