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
 * The same filters are also returned split into the scientific categories of
 * `utils/fieldGroups.ts`, which is what makes a rail of up to 150 rows readable.
 *
 * Profiling scans every column of the whole dataset, so it runs once per
 * database and is memoised for the lifetime of the page (the datasets it reads
 * never expire either).
 */
import { useDataset } from '@/composables/useDataset'
import { displaySymbol, displayUnit, useDictionaryStore } from '@/stores/dictionary'
import { FALLBACK_GROUP, groupBy, groupFor, type FieldGroupId } from '@/utils/fieldGroups'
import {
  profileColumns,
  visibleFilters,
  type FilterDescriptor,
  type FilterKind
} from '@/utils/filterProfile'
import type { DatabaseId } from '@/utils/navigation'
import type { Row } from '@/utils/queryEngine'
import {
  computed,
  ref,
  shallowReactive,
  shallowRef,
  toValue,
  type ComputedRef,
  type MaybeRefOrGetter,
  type Ref
} from 'vue'
import { useI18n } from 'vue-i18n'
import { whenIdle } from '@/utils/idle'
import { perfMark, perfMeasure } from '@/utils/perf'

export interface LabeledFilter extends FilterDescriptor {
  /** Curated i18n label when the field has one, else the dictionary description. */
  label: string
  /** Unit for display, or undefined when unitless. */
  unit?: string
  /** Symbol markup (may carry `<sub>`/`<sup>`), or undefined. */
  symbol?: string
}

/** One collapsible section of the rail (see utils/fieldGroups.ts). */
export interface FilterGroup {
  id: FieldGroupId
  label: string
  filters: LabeledFilter[]
}

export interface AutoFilterOptions<M extends { id: string }> {
  /** Which dictionary to read (see navigation.ts). */
  database: DatabaseId
  /** `useDataset` cache key — the dashboard's own, so the fetch is shared. */
  datasetKey: string
  fetchAll: () => Promise<M[]>
  /** i18n key prefix for curated field labels, e.g. `'brace.'`. */
  i18nPrefix: string
}

// Profiles outlive the components that request them: the underlying datasets are
// cached for the life of the page, so a second visit to a dashboard reuses this.
const profiles = new Map<string, FilterDescriptor[]>()

// The same profiles keyed by database, for consumers that live below the
// dashboard and only know which database they show (the table's column-header
// menus). Reactive so a table mounted before profiling finishes picks the
// descriptors up when they land.
const profilesByDatabase = shallowReactive(new Map<DatabaseId, FilterDescriptor[]>())

/**
 * The profiled descriptors of a database once its dashboard has run
 * {@link useAutoFilters} — empty until then, or when nothing profiled it.
 */
export function useFilterProfile(
  database: MaybeRefOrGetter<DatabaseId | undefined>
): ComputedRef<FilterDescriptor[]> {
  return computed(() => {
    const id = toValue(database)
    return (id && profilesByDatabase.get(id)) ?? []
  })
}

export function useAutoFilters<M extends { id: string }>(
  options: AutoFilterOptions<M>
): {
  filters: ComputedRef<LabeledFilter[]>
  groups: ComputedRef<FilterGroup[]>
  loading: Ref<boolean>
} {
  const { t, te } = useI18n({ useScope: 'global' })
  const dictionary = useDictionaryStore()
  const dataset = useDataset<M>(options.datasetKey, options.fetchAll)

  // Shallow: the profile is replaced wholesale, and deep-proxying ~70 descriptors
  // (each with its option list and histogram bins) would cost more than it buys.
  const descriptors = shallowRef<FilterDescriptor[]>(profiles.get(options.datasetKey) ?? [])
  const loading = ref<boolean>(descriptors.value.length === 0)
  if (!loading.value) profilesByDatabase.set(options.database, descriptors.value)

  function publish(profile: FilterDescriptor[]): void {
    profiles.set(options.datasetKey, profile)
    profilesByDatabase.set(options.database, profile)
    descriptors.value = profile
    loading.value = false
  }

  function profileNow(): void {
    // The one pass that is O(rows x fields): 0.7 s on connections at 10 000
    // rows (#354). It runs once per database for the life of the page, never
    // on a toggle.
    perfMark('filters:profile:start', { database: options.database })
    try {
      const profile = profileColumns(
        dataset.rowsSync() as Row[],
        dictionary.columnsFor(options.database)
      )
      perfMark('filters:profile:end', { database: options.database, fields: profile.length })
      perfMeasure('filters:profile', 'filters:profile:start', 'filters:profile:end')
      publish(profile)
      if (import.meta.env.DEV) auditProfile(options.database, profile)
    } catch {
      // Same as a missing dictionary: no auto filters, but no rail stuck on
      // "loading" either.
      loading.value = false
    }
  }

  if (loading.value) {
    Promise.all([dictionary.fetch(), dataset.ready()])
      .then(() => {
        const cached = profiles.get(options.datasetKey)
        if (cached) return publish(cached)
        // Not right away: the rows have just landed and the table and the
        // charts are about to paint them. The rail is a closed drawer at this
        // point, so its profile can wait for the main thread to go quiet;
        // until then the rail says it is loading and the chips fall back to
        // their i18n labels.
        whenIdle(profileNow)
      })
      .catch(() => {
        // A missing dictionary or dataset simply means no auto filters — the
        // dashboard's table and charts surface the failure themselves.
        loading.value = false
      })
  }

  const filters = computed<LabeledFilter[]>(() =>
    visibleFilters(descriptors.value).map((descriptor) => ({
      ...descriptor,
      label: resolveLabel(descriptor, options.i18nPrefix, t, te),
      unit: displayUnit(descriptor.column),
      symbol: displaySymbol(descriptor.column)
    }))
  )

  // The same filters, split into the collapsible sections the rail renders. Both
  // shapes are returned because the dashboard's active-filter chips still look
  // filters up by key, flat.
  const groups = computed<FilterGroup[]>(() =>
    groupBy(options.database, filters.value, (filter) => filter.column).map((group) => ({
      id: group.id,
      label: t(`field_group.${group.id}`),
      filters: group.items
    }))
  )

  return { filters, groups, loading }
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
      group: groupFor(database, descriptor.column),
      hidden_because: descriptor.hiddenReason ?? '',
      distinct: descriptor.distinct,
      filled: descriptor.nonNull,
      missing: descriptor.missing
    }))
  )
  // Columns nothing claimed pile up under one unhelpful heading, so say so loudly
  // here as well as failing fieldGroups.spec.ts.
  const orphans = profile
    .filter((descriptor) => groupFor(database, descriptor.column) === FALLBACK_GROUP)
    .map((descriptor) => descriptor.key)
  if (orphans.length > 0) {
    console.warn(`[auto-filters] ${database}: ungrouped columns`, orphans)
  }
  console.groupEnd()
}
