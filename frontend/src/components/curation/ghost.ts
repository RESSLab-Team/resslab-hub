/**
 * Ghost-mode configuration: for each database the submit flow supports, the
 * existing-dataset source and the parallel-coordinates axes the review screen
 * overlays a submission onto — the same axes as the public dashboard (moved
 * into each database's `data.ts` so there is a single source of truth).
 *
 * `cohortCandidates` are the categorical columns a curator can switch on to
 * define "similar experiments" (the mockup's comparison-cohort chips), ordered
 * from the strongest comparability signal down; `cohortDefaults` is the subset
 * pre-selected on load.
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
import { isMissing } from '@/utils/curation'
import type { DatabaseId } from '@/utils/navigation'

export interface GhostConfig {
  /** `useDataset` cache key — shared with the dashboard, so visits pre-warm. */
  key: string
  fetchAll: () => Promise<{ id: string }[]>
  fields: ParallelField<string>[]
  /** Categorical columns offered as cohort criteria, strongest signal first. */
  cohortCandidates: string[]
  /** Criteria enabled on load — a subset of `cohortCandidates`. */
  cohortDefaults: string[]
}

function config(
  key: string,
  fetchAll: () => Promise<unknown[]>,
  fields: ParallelField<string>[],
  cohortCandidates: string[],
  cohortDefaults: string[]
): GhostConfig {
  return {
    key,
    fetchAll: fetchAll as () => Promise<{ id: string }[]>,
    fields,
    cohortCandidates,
    cohortDefaults
  }
}

export const GHOST_CONFIGS: Partial<Record<DatabaseId, GhostConfig>> = {
  braces: config(
    braces.BRACE_KEY,
    braces.fetchBraces,
    braces.PARALLEL_FIELDS,
    [
      BraceField.CrossSectionShape,
      BraceField.BoundaryCondition,
      BraceField.Steel,
      BraceField.LoadingProtocol,
      BraceField.CrossSectionSize
    ],
    [BraceField.CrossSectionShape, BraceField.BoundaryCondition]
  ),
  columns: config(
    columns.COLUMN_KEY,
    columns.fetchColumns,
    columns.PARALLEL_FIELDS,
    [
      ColumnField.SectionC,
      ColumnField.SteelC,
      ColumnField.BoundaryCondition,
      ColumnField.AxisOfBending,
      ColumnField.TestProcedure
    ],
    [ColumnField.SectionC, ColumnField.SteelC]
  ),
  connections: config(
    connections.CONNECTION_KEY,
    connections.fetchConnections,
    connections.PARALLEL_FIELDS,
    [
      ConnectionField.ConnectionType,
      ConnectionField.SpecimenType,
      ConnectionField.SectionB,
      ConnectionField.SectionC,
      ConnectionField.LoadingProtocol
    ],
    [ConnectionField.ConnectionType]
  ),
  hss: config(
    hss.HSS_KEY,
    hss.fetchHsss,
    hss.PARALLEL_FIELDS,
    [
      HSSColumnField.TestConfiguration,
      HSSColumnField.TubeSection,
      HSSColumnField.SteelType,
      HSSColumnField.LoadingProtocol,
      HSSColumnField.FormingProcess
    ],
    [HSSColumnField.TestConfiguration]
  ),
  cyclic: config(
    materials.MATERIAL_KEY,
    materials.fetchMaterials,
    materials.PARALLEL_FIELDS,
    [
      MaterialField.Type,
      MaterialField.Grade,
      MaterialField.ProfileType,
      MaterialField.Profile,
      MaterialField.Lp
    ],
    [MaterialField.Type]
  ),
  residuals: config(
    residuals.RESIDUAL_KEY,
    residuals.fetchResiduals,
    residuals.PARALLEL_FIELDS,
    [
      ResidualStressField.Steel,
      ResidualStressField.ProfileType,
      ResidualStressField.Profile,
      ResidualStressField.SpecVar
    ],
    [ResidualStressField.Steel]
  )
}

/**
 * Exact set-membership query restricting the dataset to the specimens that
 * match the given cells on every selected field.
 *
 * The trailing comma per clause is what makes the match exact (see
 * `useParallelChart`'s `changeSearches`): without it `S355` would also match
 * `S355J2`. Fields the specimen does not report are skipped — an NR value
 * carries no similarity signal.
 */
export function cohortQueryFor(
  cells: Record<string, string>,
  fields: string[]
): string | undefined {
  const clauses = fields
    .filter((field) => !isMissing(cells[field]))
    .map((field) => `${field}:${(cells[field] ?? '').trim()},`)
  return clauses.length ? clauses.join(';') : undefined
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
