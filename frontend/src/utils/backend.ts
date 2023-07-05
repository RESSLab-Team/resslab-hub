export interface Page<T> {
  items: T[]
  total: number
  page?: number
  size?: number
}

export type Type = 'Braces' | 'Columns' | 'Connections' | 'Materials' | 'ResidualStresses'
export const typesNames: Type[] = [
  'Braces',
  'Columns',
  'Connections',
  'Materials',
  'ResidualStresses'
]
