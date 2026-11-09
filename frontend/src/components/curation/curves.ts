/**
 * Bridge between a submission's time-series kinds and the REST endpoints that
 * serve the same curve for specimens already in the database, so the review
 * screen can draw existing experiments underneath a submitted one.
 *
 * Keys match `TIME_SERIES_KINDS[database][].key` (asserted by the unit tests);
 * `countField` is the specimen column that says whether that curve exists, so
 * the picker can offer only specimens that actually have comparable data.
 */

import {
  bracesApi,
  columnsApi,
  connectionsApi,
  hssApi,
  materialsApi,
  residualsApi
} from '@/plugins/axios'
import { EXISTING, RED } from '@/plugins/echarts-theme'
import { slotColor } from '@/utils/categoryColors'
import type { DatabaseId } from '@/utils/navigation'
import { blendHex } from '@/utils/palette'

export interface CurveSource {
  /** Specimen column holding the number of points; 0 means "no such curve". */
  countField: string
  fetch: (id: string) => Promise<number[][]>
  /** Reshape rows the endpoint does not return as `[x, y]`. */
  transform?: (rows: number[][]) => number[][]
}

/** Points requested per curve — enough shape for a visual comparison. */
const CURVE_SIZE = 1024

/** Cyclic coupons come back as `[stress, strain]`; the chart plots ε on x. */
const swap = (rows: number[][]): number[][] => rows.map((row) => [row[1], row[0]])

export const CURVE_SOURCES: Partial<Record<DatabaseId, Record<string, CurveSource>>> = {
  braces: {
    force_displacement: {
      countField: 'displacement_count',
      fetch: (id) => bracesApi.getBracesDisplacement(id, CURVE_SIZE).then((r) => r.data)
    }
  },
  columns: {
    axial_shortening: {
      countField: 'axial_shortening_count',
      fetch: (id) => columnsApi.getColumnsAxialShortening(id, CURVE_SIZE).then((r) => r.data)
    },
    moment_strong: {
      countField: 'moment_strong_count',
      fetch: (id) => columnsApi.getColumnsMomentStrong(id, CURVE_SIZE).then((r) => r.data)
    },
    moment_weak: {
      countField: 'moment_weak_count',
      fetch: (id) => columnsApi.getColumnsMomentWeak(id, CURVE_SIZE).then((r) => r.data)
    }
  },
  connections: {
    beam: {
      countField: 'beam_count',
      fetch: (id) => connectionsApi.getConnectionsBeam(id, CURVE_SIZE).then((r) => r.data)
    },
    beam_west: {
      countField: 'beam_west_count',
      fetch: (id) => connectionsApi.getConnectionsBeamWest(id, CURVE_SIZE).then((r) => r.data)
    },
    global: {
      countField: 'global_count',
      fetch: (id) => connectionsApi.getConnectionsGlobal(id, CURVE_SIZE).then((r) => r.data)
    },
    global_west: {
      countField: 'global_west_count',
      fetch: (id) => connectionsApi.getConnectionsGlobalWest(id, CURVE_SIZE).then((r) => r.data)
    },
    panel_zone: {
      countField: 'panel_zone_count',
      fetch: (id) => connectionsApi.getConnectionsPanelZones(id, CURVE_SIZE).then((r) => r.data)
    }
  },
  hss: {
    moment_rotation: {
      countField: 'moment_rotation_count',
      fetch: (id) => hssApi.getHssColumnsMomentRotation(id, CURVE_SIZE).then((r) => r.data)
    }
  },
  cyclic: {
    stress_strain: {
      countField: 'stress_strain_count',
      fetch: (id) => materialsApi.getMaterialsStressStrain(id, CURVE_SIZE).then((r) => r.data),
      transform: swap
    }
  },
  residuals: {
    distribution_f1: {
      countField: 'distribution_F1_count',
      fetch: (id) =>
        residualsApi.getResidualStressesDistributionF1(id, CURVE_SIZE).then((r) => r.data)
    },
    distribution_f2: {
      countField: 'distribution_F2_count',
      fetch: (id) =>
        residualsApi.getResidualStressesDistributionF2(id, CURVE_SIZE).then((r) => r.data)
    },
    distribution_w1: {
      countField: 'distribution_W1_count',
      fetch: (id) =>
        residualsApi.getResidualStressesDistributionW1(id, CURVE_SIZE).then((r) => r.data)
    }
  }
}

export function curveSourceFor(
  database: DatabaseId,
  kindKey: string | undefined
): CurveSource | undefined {
  return kindKey ? CURVE_SOURCES[database]?.[kindKey] : undefined
}

/** Every count column a database's curve sources gate on. */
export function countFieldsFor(database: DatabaseId): string[] {
  return Object.values(CURVE_SOURCES[database] ?? {}).map((source) => source.countField)
}

// Session cache: a curator flipping between experiments re-requests the same
// overlay curves, and these are the heaviest payloads on the screen.
const cache = new Map<string, Promise<number[][]>>()

export function fetchCurve(database: DatabaseId, kindKey: string, id: string): Promise<number[][]> {
  const cacheKey = `${database}:${kindKey}:${id}`
  const hit = cache.get(cacheKey)
  if (hit) return hit
  const source = curveSourceFor(database, kindKey)
  if (!source) return Promise.reject(new Error(`no curve source for ${database}/${kindKey}`))
  const promise = source
    .fetch(id)
    .then((rows) => (source.transform ? source.transform(rows) : rows))
    .catch((error) => {
      cache.delete(cacheKey)
      throw error
    })
  cache.set(cacheKey, promise)
  return promise
}

// ── submitted vs existing (#268) ──────────────────────────────────────────
// One convention on the review screen and the contribution preview: what was
// submitted is drawn in red (--data-submitted), full weight; what is already in
// the database is faded toward the neutral grey (--data-existing) and thinner,
// so it stays behind. The parallel plot uses the same pair.

/** A submitted curve or row. Canvas copy of --data-submitted. */
export const SUBMITTED_COLOR = RED
/** Data already in the database. Canvas copy of --data-existing. */
export const EXISTING_COLOR = EXISTING
/** Stroke of a submitted curve. */
export const SUBMITTED_WIDTH = 1.6
/** Stroke of an existing curve: thinner, so the submission leads. */
export const EXISTING_WIDTH = 0.9
/** Opacity of an existing curve on the response-curve frames. */
export const EXISTING_OPACITY = 0.85

// Every cohort curve used to be the same grey, so with several of them on a
// frame a curator could not tell which chip was which line (andskia, #268).
// Each overlay keeps its own slot of the dashboard palette (Okabe-Ito, colour
// blind safe), mixed toward the existing-data grey so it reads as "existing"
// next to the red submission. Too strong a blend turns every hue into the same
// grey line and the chips cannot be told apart again.

/** How far the overlay hues go toward the existing-data grey. */
const OVERLAY_BLEND = 0.55

/** Colour of the nth cohort overlay on a frame. */
export function ghostColor(index: number): string {
  return blendHex(slotColor(index), EXISTING_COLOR, OVERLAY_BLEND)
}
