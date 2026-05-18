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
  | 'Cyclic Coupons'
  | 'Tensile Coupons'
  | 'Residual Stresses'
  | 'HSS Columns'
  | 'EBF Links'
export const typesNames: Type[] = [
  'Braces',
  'Columns',
  'Connections',
  'Cyclic Coupons',
  'Tensile Coupons',
  'Residual Stresses',
  'HSS Columns',
  'EBF Links'
]
