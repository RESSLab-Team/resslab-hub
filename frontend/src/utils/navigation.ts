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

export interface NavChild {
  name: string
  to: string
  /** Set when the page is a database whose row count should be displayed. */
  countId?: DatabaseId
  /** Icon + description, used by overview/footer tiles for database pages. */
  icon?: string
  desc?: string
}

export interface NavGroup {
  id: string
  name: string
  desc: string
  icon: string
  group: DatabaseGroup
  children: NavChild[]
}

export const NAV_GROUPS: NavGroup[] = [
  {
    id: 'connections',
    name: 'Connections',
    desc: 'Beam-to-column moment connections',
    icon: mdiCubeOutline,
    group: 'components',
    children: [
      { name: 'Database', to: '/connections/database', countId: 'connections' },
      { name: 'Component model', to: '/connections/model' },
      { name: 'Fragility curves', to: '/connections/fragility-curve' }
    ]
  },
  {
    id: 'columns',
    name: 'Columns',
    desc: 'Wide-flange steel column tests',
    icon: mdiLayersOutline,
    group: 'components',
    children: [
      { name: 'Database', to: '/columns/database', countId: 'columns' },
      { name: 'Component model', to: '/columns/model' },
      { name: 'Fragility curves', to: '/columns/fragility-curve' }
    ]
  },
  {
    id: 'braces',
    name: 'Braces',
    desc: 'Concentrically braced frame members',
    icon: mdiPulse,
    group: 'components',
    children: [
      { name: 'Database', to: '/braces/database', countId: 'braces' },
      { name: 'Component model', to: '/braces/model' },
      { name: 'Fragility curves', to: '/braces/fragility-curve' }
    ]
  },
  {
    id: 'hss',
    name: 'HSS Columns',
    desc: 'Hollow structural section columns',
    icon: mdiCubeOutline,
    group: 'components',
    children: [
      { name: 'Database', to: '/hss-columns/database', countId: 'hss' },
      { name: 'Component model', to: '/hss-columns/model' }
    ]
  },
  {
    id: 'ebf',
    name: 'EBF Links',
    desc: 'Eccentrically braced frame links',
    icon: mdiPulse,
    group: 'components',
    children: [{ name: 'Database', to: '/ebf-links/database', countId: 'ebf' }]
  },
  {
    id: 'materials',
    name: 'Materials',
    desc: 'Steel material characterisation',
    icon: mdiChartBar,
    group: 'materials',
    children: [
      {
        name: 'Cyclic Coupons',
        to: '/materials/cyclic-coupons',
        countId: 'cyclic',
        icon: mdiChartBar,
        desc: 'Cyclic material characterisation'
      },
      {
        name: 'Tensile Coupons',
        to: '/materials/tensile-coupons',
        countId: 'tensile',
        icon: mdiChartBellCurve,
        desc: 'Monotonic tensile test coupons'
      },
      {
        name: 'Ductile Fracture',
        to: '/materials/ductile-fracture',
        countId: 'ductile-fracture',
        icon: mdiImageFilterCenterFocus,
        desc: 'Ductile fracture tests & SEM fractography'
      },
      { name: 'Material model', to: '/materials/model' }
    ]
  },
  {
    id: 'residuals',
    name: 'Residual Stresses',
    desc: 'Cross-sectional residual stresses',
    icon: mdiLayersOutline,
    group: 'materials',
    children: [{ name: 'Database', to: '/residuals/database', countId: 'residuals' }]
  }
]

export interface DatabaseEntry {
  id: DatabaseId
  name: string
  desc: string
  icon: string
  to: string
  group: DatabaseGroup
}

/** Flat list of database pages, derived from NAV_GROUPS (overview tiles, footer). */
export const DATABASES: DatabaseEntry[] = NAV_GROUPS.flatMap((group) =>
  group.children
    .filter((child) => child.countId != null)
    .map((child) => ({
      id: child.countId as DatabaseId,
      name: child.name === 'Database' ? group.name : child.name,
      desc: child.desc ?? group.desc,
      icon: child.icon ?? group.icon,
      to: child.to,
      group: group.group
    }))
)

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
