export interface Page<T> {
  items: T[]
  total: number
  page?: number
  size?: number
}

export type Type =
  | 'Braces'
  | 'Columns'
  | 'Connections'
  | 'Materials'
  | 'Residual Stresses'
  | 'HSS Columns'
  | 'EBF Links'
  | 'Tensile Coupons'
export const typesNames: Type[] = [
  'Braces',
  'Columns',
  'Connections',
  'Materials',
  'Residual Stresses',
  'HSS Columns',
  'EBF Links',
  'Tensile Coupons'
]
