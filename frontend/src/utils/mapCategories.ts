/**
 * The databases shown on the overview map, in the design's order. The one
 * place that ties the backend `MapCategory` to a colour, a label and a route.
 */
import { MapCategory } from '@/backend'
import { colorPalette } from '@/utils/palette'

export interface MapCategoryEntry {
  id: MapCategory
  /** i18n key of the label */
  labelKey: string
  /** the database page (checked against DATABASES in the spec) */
  to: string
  color: string
}

// The 8 Okabe-Ito slots, then a grey for the 9th (as in the design). The map
// has its own fixed order here, unrelated to the dashboards' categoryColors.
export const MAP_CATEGORIES: MapCategoryEntry[] = [
  { id: MapCategory.Braces, labelKey: 'map.category_braces', to: '/braces/database' },
  { id: MapCategory.Columns, labelKey: 'map.category_columns', to: '/columns/database' },
  {
    id: MapCategory.Connections,
    labelKey: 'map.category_connections',
    to: '/connections/database'
  },
  {
    id: MapCategory.Materials,
    labelKey: 'map.category_cyclic_coupons',
    to: '/materials/cyclic-coupons'
  },
  {
    id: MapCategory.TensileCoupon,
    labelKey: 'map.category_tensile_coupons',
    to: '/materials/tensile-coupons'
  },
  {
    id: MapCategory.DuctileFracture,
    labelKey: 'map.category_ductile_fracture',
    to: '/materials/ductile-fracture'
  },
  {
    id: MapCategory.ResidualStress,
    labelKey: 'map.category_residual_stresses',
    to: '/residuals/database'
  },
  { id: MapCategory.HssColumn, labelKey: 'map.category_hss_columns', to: '/hss-columns/database' },
  {
    id: MapCategory.EccentricBracedFrame,
    labelKey: 'map.category_ebf_links',
    to: '/ebf-links/database'
  }
].map((entry, i) => ({ ...entry, color: colorPalette[i] ?? '#A6A6A6' }))

const BY_ID = new Map(MAP_CATEGORIES.map((entry, i) => [entry.id, { entry, index: i }]))

export function categoryFor(id: MapCategory): MapCategoryEntry {
  const found = BY_ID.get(id)
  if (!found) throw new Error(`unknown map category: ${id}`)
  return found.entry
}

/** Position in MAP_CATEGORIES, also the `t<i>` property of the map features. */
export function categoryIndex(id: MapCategory): number {
  return BY_ID.get(id)?.index ?? -1
}

export function colorFor(id: MapCategory): string {
  return categoryFor(id).color
}

export function routeFor(id: MapCategory): string {
  return categoryFor(id).to
}
