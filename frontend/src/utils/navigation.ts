import i18n from '@/plugins/i18n'

// The lists below are functions, not constants: each call reads the current
// locale, so a component that wraps them in `computed` follows a language
// switch. A constant would keep the language of the first import.
const t = i18n.global.t

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

export function navGroups(): NavGroup[] {
  return [
    {
      id: 'connections',
      name: t('nav.connections'),
      desc: t('nav.connections_desc'),
      icon: 'rl:connections',
      group: 'components',
      children: [
        { name: t('nav.database'), to: '/connections/database', countId: 'connections' },
        { name: t('nav.component_model'), to: '/connections/model' },
        { name: t('nav.fragility_curves'), to: '/connections/fragility-curve' }
      ]
    },
    {
      id: 'columns',
      name: t('nav.columns'),
      desc: t('nav.columns_desc'),
      icon: 'rl:columns',
      group: 'components',
      children: [
        { name: t('nav.database'), to: '/columns/database', countId: 'columns' },
        { name: t('nav.component_model'), to: '/columns/model' },
        { name: t('nav.fragility_curves'), to: '/columns/fragility-curve' }
      ]
    },
    {
      id: 'braces',
      name: t('nav.braces'),
      desc: t('nav.braces_desc'),
      icon: 'rl:braces',
      group: 'components',
      children: [
        { name: t('nav.database'), to: '/braces/database', countId: 'braces' },
        { name: t('nav.component_model'), to: '/braces/model' },
        { name: t('nav.fragility_curves'), to: '/braces/fragility-curve' }
      ]
    },
    {
      id: 'hss',
      name: t('nav.hss_columns'),
      desc: t('nav.hss_columns_desc'),
      icon: 'rl:hss',
      group: 'components',
      children: [
        { name: t('nav.database'), to: '/hss-columns/database', countId: 'hss' },
        { name: t('nav.component_model'), to: '/hss-columns/model' }
      ]
    },
    {
      id: 'ebf',
      name: t('nav.ebf_links'),
      desc: t('nav.ebf_links_desc'),
      icon: 'rl:ebf',
      group: 'components',
      children: [{ name: t('nav.database'), to: '/ebf-links/database', countId: 'ebf' }]
    },
    {
      id: 'materials',
      name: t('nav.materials'),
      desc: t('nav.materials_desc'),
      icon: 'rl:materials',
      group: 'materials',
      children: [
        {
          name: t('nav.cyclic_coupons'),
          to: '/materials/cyclic-coupons',
          countId: 'cyclic',
          icon: 'rl:cyclic',
          desc: t('nav.cyclic_coupons_desc')
        },
        {
          name: t('nav.tensile_coupons'),
          to: '/materials/tensile-coupons',
          countId: 'tensile',
          icon: 'rl:tensile',
          desc: t('nav.tensile_coupons_desc')
        },
        {
          name: t('nav.ductile_fracture'),
          to: '/materials/ductile-fracture',
          countId: 'ductile-fracture',
          icon: 'rl:ductile-fracture',
          desc: t('nav.ductile_fracture_desc')
        },
        { name: t('nav.material_model'), to: '/materials/model', icon: 'rl:materials' }
      ]
    },
    {
      id: 'residuals',
      name: t('nav.residual_stresses'),
      desc: t('nav.residual_stresses_desc'),
      icon: 'rl:residuals',
      group: 'materials',
      children: [{ name: t('nav.database'), to: '/residuals/database', countId: 'residuals' }]
    }
  ]
}

export interface DatabaseEntry {
  id: DatabaseId
  name: string
  desc: string
  icon: string
  to: string
  group: DatabaseGroup
}

/**
 * Flat list of database pages, derived from navGroups() (overview tiles,
 * footer). A group's own "Database" page takes the group's name; the material
 * pages keep theirs.
 */
export function databases(): DatabaseEntry[] {
  return navGroups().flatMap((group) =>
    group.children
      .filter((child) => child.countId != null)
      .map((child) => ({
        id: child.countId as DatabaseId,
        name: child.to.endsWith('/database') ? group.name : child.name,
        desc: child.desc ?? group.desc,
        icon: child.icon ?? group.icon,
        to: child.to,
        group: group.group
      }))
  )
}

export interface ToolEntry {
  name: string
  desc: string
  to: string
}

export function tools(): ToolEntry[] {
  return [
    {
      name: t('nav.component_models'),
      desc: t('nav.component_models_desc'),
      to: '/connections/model'
    },
    {
      name: t('nav.fragility_curves'),
      desc: t('nav.fragility_curves_desc'),
      to: '/connections/fragility-curve'
    },
    {
      name: t('nav.material_model'),
      desc: t('nav.material_model_desc'),
      to: '/materials/model'
    }
  ]
}
