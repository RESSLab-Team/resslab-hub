import snapshotJson from '@/assets/kpi-snapshot.json'
import type { DatabaseId } from '@/utils/navigation'

/**
 * Committed snapshot of the homepage KPIs, refreshed by `npm run kpi:snapshot`
 * (scripts/update-kpi-snapshot.mjs). Seeds the key-numbers band and sidebar
 * badges so they render on first paint; the live fetch overwrites them.
 */
export interface KpiSnapshot {
  generatedAt: string
  counts: Partial<Record<DatabaseId, number>>
  sources: Partial<Record<DatabaseId, number>>
  universities: number | null
  users: number | null
}

/** Per-KPI stale-while-revalidate state, driving the bar under each number. */
export type KpiStatus = 'loading' | 'live' | 'stale'

export const kpiSnapshot: KpiSnapshot = snapshotJson
