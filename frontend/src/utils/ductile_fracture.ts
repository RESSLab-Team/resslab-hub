import type { DuctileFractureModel } from '@/backend'
import { ductileFractureApi } from '@/plugins/axios'
import i18n from '@/plugins/i18n'
import type { AxiosResponse } from 'axios'

export function displayLoading(loading: string | null | undefined): string {
  if (!loading) return ''
  if (loading.toLowerCase().includes('cyclic')) return i18n.global.t('enum.cyclic')
  if (loading.toLowerCase().includes('monotonic')) return i18n.global.t('enum.monotonic')
  return loading
}

export type DuctileFracturePlotId = 'force-axial' | 'force-radial' | 'triax' | 'lode' | 'epeq'

type SeriesFetcher = (id: string) => Promise<AxiosResponse<number[][]>>

export interface DuctileFracturePlotConfig {
  id: DuctileFracturePlotId
  title: string
  xAxisName: string
  yAxisName: string
  testFetcher?: SeriesFetcher
  simulationFetcher?: SeriesFetcher
  hasTest: (m: DuctileFractureModel) => boolean
  hasSimulation: (m: DuctileFractureModel) => boolean
}

export const ductileFracturePlots: Record<DuctileFracturePlotId, DuctileFracturePlotConfig> = {
  'force-axial': {
    id: 'force-axial',
    title: i18n.global.t('enum.forceAxialElongation'),
    xAxisName: i18n.global.t('enum.axialElongationMm'),
    yAxisName: i18n.global.t('enum.forceKn'),
    testFetcher: (id) => ductileFractureApi.getDuctileFracturesForceElongation(id),
    simulationFetcher: (id) => ductileFractureApi.getDuctileFracturesForceElongationSimulation(id),
    hasTest: (m) => m.force_elongation_count > 0,
    hasSimulation: (m) => m.force_elongation_simulation_count > 0
  },
  'force-radial': {
    id: 'force-radial',
    title: i18n.global.t('enum.forceRadialElongation'),
    xAxisName: i18n.global.t('enum.radialElongationMm'),
    yAxisName: i18n.global.t('enum.forceKn'),
    testFetcher: (id) => ductileFractureApi.getDuctileFracturesForceRadial(id),
    simulationFetcher: (id) => ductileFractureApi.getDuctileFracturesForceRadialSimulation(id),
    hasTest: (m) => m.force_radial_count > 0,
    hasSimulation: (m) => m.force_radial_simulation_count > 0
  },
  triax: {
    id: 'triax',
    title: i18n.global.t('enum.triaxialityHistory'),
    xAxisName: i18n.global.t('enum.axialElongationMm'),
    yAxisName: i18n.global.t('enum.triaxiality'),
    simulationFetcher: (id) => ductileFractureApi.getDuctileFracturesTriaxSimulation(id),
    hasTest: () => false,
    hasSimulation: (m) => m.triax_simulation_count > 0
  },
  lode: {
    id: 'lode',
    title: i18n.global.t('enum.lodeAngleHistory'),
    xAxisName: i18n.global.t('enum.axialElongationMm'),
    yAxisName: i18n.global.t('enum.lodeAngle'),
    simulationFetcher: (id) => ductileFractureApi.getDuctileFracturesLodeSimulation(id),
    hasTest: () => false,
    hasSimulation: (m) => m.lode_simulation_count > 0
  },
  epeq: {
    id: 'epeq',
    title: i18n.global.t('enum.equivalentPlasticStrainHistory'),
    xAxisName: i18n.global.t('enum.axialElongationMm'),
    yAxisName: 'εp',
    simulationFetcher: (id) => ductileFractureApi.getDuctileFracturesEpeqSimulation(id),
    hasTest: () => false,
    hasSimulation: (m) => m.epeq_simulation_count > 0
  }
}
