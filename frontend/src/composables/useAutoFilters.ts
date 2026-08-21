/**
 * The filter list for a dashboard, derived instead of declared.
 *
 * Joins the two sources that already describe a database — the data dictionary
 * (`GET /dictionary`: every column's type, symbol, unit and description) and the
 * dataset `useDataset` has already cached in the browser — and hands the rail a
 * ready-to-render list of typed filters. Adding a column to a data dictionary is
 * therefore all it takes for a filter to appear; no dashboard lists fields any
 * more.
 *
 * Profiling scans every column of the whole dataset, so it runs once per
 * database and is memoised for the lifetime of the page (the datasets it reads
 * never expire either).
 */
import { useDataset } from '@/composables/useDataset'
import { displaySymbol, displayUnit, useDictionaryStore } from '@/stores/dictionary'
import {
  profileColumns,
  visibleFilters,
  type FilterDescriptor,
  type FilterKind
} from '@/utils/filterProfile'
import type { DatabaseId } from '@/utils/navigation'
import type { Row } from '@/utils/queryEngine'
import { computed, ref, shallowRef, type ComputedRef, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'

export interface LabeledFilter extends FilterDescriptor {
  /** Curated i18n label when the field has one, else the dictionary description. */
  label: string
  /** Unit for display, or undefined when unitless. */
  unit?: string
  /** Symbol markup (may carry `<sub>`/`<sup>`), or undefined. */
  symbol?: string
}

export interface AutoFilterOptions<M extends { id: string }> {
  /** Which dictionary to read (see navigation.ts). */
  database: DatabaseId
  /** `useDataset` cache key — the dashboard's own, so the fetch is shared. */
  datasetKey: string
  fetchAll: () => Promise<M[]>
  /** i18n key prefix for curated field labels, e.g. `'brace.'`. */
  i18nPrefix: string
  /**
   * Fields to float to the top of the rail — the handful each dashboard used to
   * declare by hand. Everything else follows in data-dictionary order.
   */
  pinned?: string[]
}

// Profiles outlive the components that request them: the underlying datasets are
// cached for the life of the page, so a second visit to a dashboard reuses this.
const profiles = new Map<string, FilterDescriptor[]>()

export function useAutoFilters<M extends { id: string }>(
  options: AutoFilterOptions<M>
): { filters: ComputedRef<LabeledFilter[]>; loading: Ref<boolean> } {
  const { t, te } = useI18n({ useScope: 'global' })
  const dictionary = useDictionaryStore()
  const dataset = useDataset<M>(options.datasetKey, options.fetchAll)

  // Shallow: the profile is replaced wholesale, and deep-proxying ~70 descriptors
  // (each with its option list and histogram bins) would cost more than it buys.
  const descriptors = shallowRef<FilterDescriptor[]>(profiles.get(options.datasetKey) ?? [])
  const loading = ref<boolean>(descriptors.value.length === 0)

  if (loading.value) {
    Promise.all([dictionary.fetch(), dataset.ready()])
      .then(() => {
        const cached = profiles.get(options.datasetKey)
        const profile =
          cached ??
          profileColumns(dataset.rowsSync() as Row[], dictionary.columnsFor(options.database))
        profiles.set(options.datasetKey, profile)
        descriptors.value = profile
        if (import.meta.env.DEV && !cached) auditProfile(options.database, profile)
      })
      .catch(() => {
        // A missing dictionary or dataset simply means no auto filters — the
        // dashboard's table and charts surface the failure themselves.
      })
      .finally(() => {
        loading.value = false
      })
  }

  const filters = computed<LabeledFilter[]>(() => {
    const labeled = visibleFilters(descriptors.value).map((descriptor) => ({
      ...descriptor,
      label: resolveLabel(descriptor, options.i18nPrefix, t, te),
      unit: displayUnit(descriptor.column),
      symbol: displaySymbol(descriptor.column)
    }))
    return sortPinnedFirst(labeled, options.pinned)
  })

  return { filters, loading }
}

/**
 * Curated translation first (only a fraction of columns have one), then the
 * dictionary description, then the raw column name. French falls back to the
 * English description for the long tail — the dictionary is English-only.
 */
function resolveLabel(
  descriptor: FilterDescriptor,
  prefix: string,
  t: (key: string) => string,
  te: (key: string) => boolean
): string {
  const key = `${prefix}${descriptor.key}`
  if (te(key)) return t(key)
  const description = descriptor.column.description?.trim()
  return description && description !== '-' ? description : descriptor.key
}

/** Pinned fields keep the order they were given; the rest stay in dictionary order. */
function sortPinnedFirst(filters: LabeledFilter[], pinned?: string[]): LabeledFilter[] {
  if (!pinned?.length) return filters
  const rank = new Map(pinned.map((key, index) => [key, index]))
  const top = filters
    .filter((filter) => rank.has(filter.key))
    .sort((a, b) => rank.get(a.key)! - rank.get(b.key)!)
  const rest = filters.filter((filter) => !rank.has(filter.key))
  return [...top, ...rest]
}

/**
 * Dev-only audit of what the heuristics decided, so a maintainer can check a
 * database's classification (and what got dropped, and why) at a glance.
 */
function auditProfile(database: DatabaseId, profile: FilterDescriptor[]): void {
  const byKind = profile.reduce<Record<string, number>>((tally, descriptor) => {
    const kind: FilterKind = descriptor.kind
    tally[kind] = (tally[kind] ?? 0) + 1
    return tally
  }, {})
  console.groupCollapsed(
    `[auto-filters] ${database}: ${profile.length} columns → ` +
      Object.entries(byKind)
        .map(([kind, count]) => `${count} ${kind}`)
        .join(', ')
  )
  console.table(
    profile.map((descriptor) => ({
      column: descriptor.key,
      type: descriptor.column.type,
      kind: descriptor.kind,
      hidden_because: descriptor.hiddenReason ?? '',
      distinct: descriptor.distinct,
      filled: descriptor.nonNull,
      missing: descriptor.missing
    }))
  )
  console.groupEnd()
}
