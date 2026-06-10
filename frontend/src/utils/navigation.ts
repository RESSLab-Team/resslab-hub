import {
  mdiChartBar,
  mdiChartBellCurve,
  mdiCubeOutline,
  mdiImageFilterCenterFocus,
  mdiLayersOutline,
  mdiPulse
} from '@mdi/js'

export type DatabaseId =
  | 'connections'
  | 'columns'
  | 'braces'
  | 'hss'
  | 'ebf'
  | 'cyclic'
  | 'tensile'
  | 'ductile-fracture'
  | 'residuals'

export type DatabaseGroup = 'components' | 'materials'

export interface DatabaseEntry {
  id: DatabaseId
  name: string
  desc: string
  icon: string
  to: string
  group: DatabaseGroup
}

export const DATABASES: DatabaseEntry[] = [
  {
    id: 'connections',
    name: 'Connections',
    desc: 'Beam-to-column moment connections',
    icon: mdiCubeOutline,
    to: '/connections/database',
    group: 'components'
  },
  {
    id: 'columns',
    name: 'Columns',
    desc: 'Wide-flange steel column tests',
    icon: mdiLayersOutline,
    to: '/columns/database',
    group: 'components'
  },
  {
    id: 'braces',
    name: 'Braces',
    desc: 'Concentrically braced frame members',
    icon: mdiPulse,
    to: '/braces/database',
    group: 'components'
  },
  {
    id: 'hss',
    name: 'HSS Columns',
    desc: 'Hollow structural section columns',
    icon: mdiCubeOutline,
    to: '/hss-columns/database',
    group: 'components'
  },
  {
    id: 'ebf',
    name: 'EBF Links',
    desc: 'Eccentrically braced frame links',
    icon: mdiPulse,
    to: '/ebf-links/database',
    group: 'components'
  },
  {
    id: 'cyclic',
    name: 'Cyclic Coupons',
    desc: 'Cyclic material characterisation',
    icon: mdiChartBar,
    to: '/materials/cyclic-coupons',
    group: 'materials'
  },
  {
    id: 'tensile',
    name: 'Tensile Coupons',
    desc: 'Monotonic tensile test coupons',
    icon: mdiChartBellCurve,
    to: '/materials/tensile-coupons',
    group: 'materials'
  },
  {
    id: 'ductile-fracture',
    name: 'Ductile Fracture',
    desc: 'Ductile fracture tests & SEM fractography',
    icon: mdiImageFilterCenterFocus,
    to: '/materials/ductile-fracture',
    group: 'materials'
  },
  {
    id: 'residuals',
    name: 'Residual Stresses',
    desc: 'Cross-sectional residual stresses',
    icon: mdiLayersOutline,
    to: '/residuals/database',
    group: 'materials'
  }
]

export interface ToolEntry {
  name: string
  desc: string
  to: string
}

export const TOOLS: ToolEntry[] = [
  {
    name: 'Component models',
    desc: 'Backbone & first-cycle envelope curves',
    to: '/connections/model'
  },
  {
    name: 'Fragility curves',
    desc: 'Univariate / multivariate curves',
    to: '/connections/fragility-curve'
  },
  {
    name: 'Material model',
    desc: 'Voce-Chaboche calibration tool',
    to: '/materials/model'
  }
]
