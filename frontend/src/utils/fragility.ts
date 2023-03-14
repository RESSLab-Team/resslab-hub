import cdf from '@stdlib/stats-base-dists-lognormal-cdf'
import type { EChartsOption } from 'echarts'
import { range } from 'lodash'
import { getColorMap } from './vuetify'

function storyDriftRatio(median: number): number[] {
  return range(0, median * 2.5, 0.01)
}

export function fragilityCurve(
  median: number,
  sigma: number,
  maxMedian = median,
  maxSdr?: number
): [number, number][] {
  const sdr = maxSdr ? range(0, maxSdr, 0.01) : storyDriftRatio(maxMedian)
  const medianLog = Math.log(median)
  return sdr.map((value) => [value, cdf(value, medianLog, sigma)])
}

export interface DamageState {
  median: number
  beta: number
}

export function univariateOption(
  damageStates: DamageState[],
  maxSdr?: number,
  namePrefix = ''
): EChartsOption {
  const colorPalette = getColorMap(damageStates.length)
  const maxMedian = Math.max(...damageStates.map((state) => state.median))
  return {
    xAxis: {
      name: 'SDR'
    },
    yAxis: {
      name: 'P(DS)'
    },
    series: damageStates.map((state, index) => ({
      type: 'line',
      name: namePrefix + `DS${index + 1}`,
      showSymbol: false,
      animation: false,
      itemStyle: {
        color: colorPalette[index]
      },
      lineStyle: {
        color: colorPalette[index]
      },
      data: fragilityCurve(state.median, state.beta, maxMedian, maxSdr)
    }))
  }
}
