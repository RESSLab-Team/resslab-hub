import { ductileFractureApi } from '@/plugins/axios'
import type { DuctileFractureModel } from '@/backend'
import type { AxiosResponse } from 'axios'

export function displayLoading(loading: string | null | undefined): string {
  if (!loading) return ''
  if (loading.toLowerCase().includes('cyclic')) return 'Cyclic'
  if (loading.toLowerCase().includes('monotonic')) return 'Monotonic'
  return loading
}

export type DuctileFracturePlotId =
  | 'force-axial'
  | 'force-radial'
  | 'triax'
  | 'lode'
  | 'epeq'

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
    title: 'Force-axial elongation',
    xAxisName: 'Axial elongation [mm]',
    yAxisName: 'Force [kN]',
    testFetcher: (id) => ductileFractureApi.getDuctileFracturesForceElongation(id),
    simulationFetcher: (id) => ductileFractureApi.getDuctileFracturesForceElongationSimulation(id),
    hasTest: (m) => m.force_elongation_count > 0,
    hasSimulation: (m) => m.force_elongation_simulation_count > 0
  },
  'force-radial': {
    id: 'force-radial',
    title: 'Force-radial elongation',
    xAxisName: 'Radial elongation [mm]',
    yAxisName: 'Force [kN]',
    testFetcher: (id) => ductileFractureApi.getDuctileFracturesForceRadial(id),
    simulationFetcher: (id) => ductileFractureApi.getDuctileFracturesForceRadialSimulation(id),
    hasTest: (m) => m.force_radial_count > 0,
    hasSimulation: (m) => m.force_radial_simulation_count > 0
  },
  triax: {
    id: 'triax',
    title: 'Triaxiality history',
    xAxisName: 'Axial elongation [mm]',
    yAxisName: 'Triaxiality',
    simulationFetcher: (id) => ductileFractureApi.getDuctileFracturesTriaxSimulation(id),
    hasTest: () => false,
    hasSimulation: (m) => m.triax_simulation_count > 0
  },
  lode: {
    id: 'lode',
    title: 'Lode angle history',
    xAxisName: 'Axial elongation [mm]',
    yAxisName: 'Lode angle',
    simulationFetcher: (id) => ductileFractureApi.getDuctileFracturesLodeSimulation(id),
    hasTest: () => false,
    hasSimulation: (m) => m.lode_simulation_count > 0
  },
  epeq: {
    id: 'epeq',
    title: 'Equivalent plastic strain history',
    xAxisName: 'Axial elongation [mm]',
    yAxisName: 'εp',
    simulationFetcher: (id) => ductileFractureApi.getDuctileFracturesEpeqSimulation(id),
    hasTest: () => false,
    hasSimulation: (m) => m.epeq_simulation_count > 0
  }
}
