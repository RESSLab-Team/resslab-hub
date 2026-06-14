<script setup lang="ts">
// Computations from https://github.com/RESSLab-Team/resslab-hub-scripts/tree/main/fragility_curves_steel_braces
import UnitChart from '@/components/commons/charts/UnitChart.vue'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SimpleToggle from '@/components/commons/SimpleToggle.vue'
import TitleRow from '@/components/commons/TitleRow.vue'
import type { EChartsGlOption } from '@/utils/echarts-gl'
import { univariateOption, type DamageState } from '@/utils/fragility'
import type { ToggleItem } from '@/utils/toggle'
import { getColorMap } from '@/utils/vuetify'
import cdf from '@stdlib/stats-base-dists-lognormal-cdf'
import type { EChartsOption } from 'echarts'
import { range, zip } from 'lodash'
import { index, Matrix, matrix, max, sum } from 'mathjs'
import { computed, defineAsyncComponent, ref } from 'vue'

// Lazy-load the 3D surface so the heavy echarts-gl (WebGL) bundle only loads
// when a 3D plot is actually rendered.
const SurfaceGlChart = defineAsyncComponent(
  () => import('@/components/commons/charts/SurfaceGlChart.vue')
)

type Option = 'square-hss' | 'round-hss' | 'w-shape' | 'l-shape'

const damageStates: Record<Option, DamageState[]> = {
  'square-hss': [
    {
      median: 0.4,
      beta: 0.43
    },
    {
      median: 1.02,
      beta: 0.44
    },
    {
      median: 1.6,
      beta: 0.48
    }
  ],
  'round-hss': [
    {
      median: 0.4,
      beta: 0.43
    },
    {
      median: 1.02,
      beta: 0.44
    },
    {
      median: 1.6,
      beta: 0.48
    }
  ],
  'w-shape': [
    {
      median: 0.3,
      beta: 0.58
    },
    {
      median: 1.01,
      beta: 0.54
    },
    {
      median: 3.1,
      beta: 0.41
    }
  ],
  'l-shape': [
    {
      median: 0.27,
      beta: 0.51
    },
    {
      median: 0.7,
      beta: 0.65
    },
    {
      median: 1.43,
      beta: 0.52
    }
  ]
}
const options: ToggleItem<Option>[] = [
  {
    value: 'square-hss',
    text: 'Square HSS'
  },
  {
    value: 'round-hss',
    text: 'Round HSS'
  },
  {
    value: 'w-shape',
    text: 'Wide-Flange'
  },
  {
    value: 'l-shape',
    text: 'Angle (L-shape)'
  }
]
/**
 * Global slenderness KL/r
 */
const slendernesses: Record<Option, DamageState[]> = {
  'square-hss': [
    {
      median: 62.8,
      beta: 0.33
    },
    {
      median: 62.5,
      beta: 0.33
    },
    {
      median: 62.3,
      beta: 0.35
    }
  ],
  'round-hss': [
    {
      median: 63.6,
      beta: 0.46
    },
    {
      median: 66.1,
      beta: 0.45
    },
    {
      median: 68.9,
      beta: 0.4
    }
  ],
  'w-shape': [
    {
      median: 62.9,
      beta: 0.47
    },
    {
      median: 64.5,
      beta: 0.45
    },
    {
      median: 72.3,
      beta: 0.37
    }
  ],
  'l-shape': [
    {
      median: 76.8,
      beta: 0.45
    },
    {
      median: 81.5,
      beta: 0.44
    },
    {
      median: 97.3,
      beta: 0.39
    }
  ]
}

const option = ref<Option>('square-hss')

const univariateOptions = computed<Record<Option, EChartsOption>>(() => {
  return Object.fromEntries(
    Object.entries(damageStates).map(([key, value]) => [key, univariateOption(value)])
  ) as Record<Option, EChartsOption>
})

const multivariateOptions = computed<EChartsGlOption[]>(() => {
  const tuples = zip(damageStates[option.value], slendernesses[option.value]).filter(
    (item): item is [DamageState, DamageState] => item[0] !== undefined && item[1] !== undefined
  )
  const colorPalette = getColorMap(tuples.length)
  return tuples.map(([ds, kl], i) =>
    correlatedBivariateOption(ds, kl, (i + 1).toString(), colorPalette[i])
  )
})

function correlatedBivariateOption(
  ds: DamageState,
  kl: DamageState,
  name: string,
  color: string
): EChartsGlOption {
  const xRange = range(0.0001, 0.05, 0.005)
  const yRange = range(10, 105, 5)
  return {
    grid3D: {
      viewControl: {
        distance: 300
      }
    },
    xAxis3D: {
      name: 'SDR [rad]'
    },
    yAxis3D: {
      name: 'KL/r'
    },
    zAxis3D: {
      name: `P(DS${name})`
    },
    series: [
      {
        type: 'surface',
        name: '',
        wireframe: {
          show: false
        },
        itemStyle: {
          color
        },
        data: correlatedBivariate(xRange, yRange, ds, kl),
        dataShape: [xRange.length, yRange.length]
      }
    ]
  }
}

function correlatedBivariate(
  xs: number[],
  ys: number[],
  ds: DamageState,
  kl: DamageState,
  corr = 0
): [number, number, number][] {
  const median1 = ds.median / 100
  const median2 = kl.median
  const sigma1 = ds.beta
  const sigma2 = kl.beta
  const muln1 = Math.log(median1) - Math.pow(sigma1, 2) / 2
  const muln2 = Math.log(median2) - Math.pow(sigma2, 2) / 2

  const pdfMatrix: Matrix = matrix()
  for (let i = 0; i < xs.length; i++) {
    const x = xs[i]
    const a1 = Math.log(x) - muln1
    for (let j = 0; j < ys.length; j++) {
      const y = ys[j]
      const a2 = Math.log(y) - muln2
      const q =
        (1 / (1 - Math.pow(corr, 2))) *
        (Math.pow(a1, 2) / Math.pow(sigma1, 2) -
          (2 * corr * a1 * a2) / (sigma1 * sigma2) +
          Math.pow(a2, 2) / Math.pow(sigma2, 2))
      pdfMatrix.set(
        [i, j],
        (1 / (2 * Math.PI * x * y * sigma1 * sigma2 * Math.pow(1 - Math.pow(corr, 2), 0.5))) *
          Math.exp(-q / 2)
      )
    }
  }

  let cdfMatrix: Matrix = matrix()
  const allIRange = range(0, xs.length)
  const allJRange = range(0, ys.length)
  for (let i = 0; i < xs.length; i++) {
    const iRange = range(0, i + 1)
    const sum2 = sum(pdfMatrix.subset(index(iRange, allJRange)))
    for (let j = 0; j < ys.length; j++) {
      const jRange = range(0, j + 1)
      const sum3 = sum(pdfMatrix.subset(index(iRange, jRange)))
      const sum1 = sum(pdfMatrix.subset(index(allIRange, jRange)))
      cdfMatrix.set([i, j], (sum1 as number) + (sum2 as number) - (sum3 as number))
    }
  }

  cdfMatrix = cdfMatrix.map((value, index) => {
    const i = index as unknown as [number, number]
    return value * cdf(xs[i[0]], muln1, sigma1) * cdf(ys[i[1]], muln2, sigma2)
  })

  const maxValue = max(cdfMatrix)
  cdfMatrix = cdfMatrix.map((v) => v / (maxValue as number))

  const data: [number, number, number][] = []
  for (let i = 0; i < xs.length; i++) {
    for (let j = 0; j < ys.length; j++) {
      data.push([xs[i], ys[j], cdfMatrix.get([i, j])])
    }
  }
  return data
}
</script>

<template>
  <v-row>
    <v-col cols="12">
      <title-row>
        <h1>Fragility Curve Plotter for Steel Bracings</h1>
        <p>
          This interactive module plots univariate and multivariate fragility curves for steel
          bracings of various types of cross sections. the multivariate curves depict the dependence
          of the fragility curve on member slenderness. For further information refer to
          <a
            href="https://www.sciencedirect.com/science/article/abs/pii/S0143974X13002277"
            target="_blank"
            >Lignos and Karamanci (2013)</a
          >.
        </p>
      </title-row>
    </v-col>
    <v-col cols="12">
      <simple-toggle v-model="option" :items="options" />
      <info-tooltip>
        Select the appropriate cross sectional shape of the bracing member to visualize the
        corresponding fragility curve.
      </info-tooltip>
    </v-col>
    <v-col cols="4">
      <h2>Univariate Fragilities</h2>
      <unit-chart :aspect-ratio="2" :option="univariateOptions[option]" x-unit="rad" />
    </v-col>
    <v-col cols="8">
      <h2>Multivariate Fragilities</h2>
      <v-row>
        <v-col v-for="(item, i) in multivariateOptions" :key="i" cols="4">
          <surface-gl-chart :aspect-ratio="1" :option="item" />
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
