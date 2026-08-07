/**
 * Ghost-mode configuration: for each database the submit flow supports, the
 * existing-dataset source and the parallel-coordinates axes the review screen
 * overlays a submission onto — the same axes as the public dashboard (moved
 * into each database's `data.ts` so there is a single source of truth).
 *
 * `cohortFields` are the categorical columns that define "similar experiments"
 * for the like-for-like cohort filter (the mockup's comparison-cohort chips).
 */

import {
  BraceField,
  ColumnField,
  ConnectionField,
  HSSColumnField,
  MaterialField,
  ResidualStressField
} from '@/backend'
import * as braces from '@/components/braces/data'
import * as columns from '@/components/columns/data'
import * as connections from '@/components/connections/data'
import * as hss from '@/components/hss/data'
import * as materials from '@/components/materials/data'
import * as residuals from '@/components/residuals/data'
import { isDivision, type ParallelField } from '@/composables/chart'
import type { DatabaseId } from '@/utils/navigation'

export interface GhostConfig {
  /** `useDataset` cache key — shared with the dashboard, so visits pre-warm. */
  key: string
  fetchAll: () => Promise<{ id: string }[]>
  fields: ParallelField<string>[]
  cohortFields: string[]
}

function config(
  key: string,
  fetchAll: () => Promise<unknown[]>,
  fields: ParallelField<string>[],
  cohortFields: string[]
): GhostConfig {
  return {
    key,
    fetchAll: fetchAll as () => Promise<{ id: string }[]>,
    fields,
    cohortFields
  }
}

export const GHOST_CONFIGS: Partial<Record<DatabaseId, GhostConfig>> = {
  braces: config(braces.BRACE_KEY, braces.fetchBraces, braces.PARALLEL_FIELDS, [
    BraceField.CrossSectionShape,
    BraceField.BoundaryCondition
  ]),
  columns: config(columns.COLUMN_KEY, columns.fetchColumns, columns.PARALLEL_FIELDS, [
    ColumnField.SectionC,
    ColumnField.SteelC
  ]),
  connections: config(
    connections.CONNECTION_KEY,
    connections.fetchConnections,
    connections.PARALLEL_FIELDS,
    [ConnectionField.ConnectionType]
  ),
  hss: config(hss.HSS_KEY, hss.fetchHsss, hss.PARALLEL_FIELDS, [HSSColumnField.TestConfiguration]),
  cyclic: config(materials.MATERIAL_KEY, materials.fetchMaterials, materials.PARALLEL_FIELDS, [
    MaterialField.Type
  ]),
  residuals: config(residuals.RESIDUAL_KEY, residuals.fetchResiduals, residuals.PARALLEL_FIELDS, [
    ResidualStressField.Steel
  ])
}

/** Flat request-field list for a set of parallel axes (division axes expand). */
export function requestFieldsFor(fields: ParallelField<string>[]): string[] {
  const flat = fields.flatMap((field) => {
    if (typeof field.id === 'string') return [field.id]
    if (isDivision(field.id)) return [field.id.dividend, field.id.divisor]
    return field.id.fields
  })
  return [...new Set(flat)]
}
