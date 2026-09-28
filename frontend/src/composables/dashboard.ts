import type { Page } from '@/utils/backend'
import {
  debounceAPITime,
  filterColumnValue,
  globalSearchKey,
  type Searches,
  type Value
} from '@/utils/common'
import { debounce } from 'lodash'
import { computed, provide, ref, triggerRef, unref, watch, type InjectionKey, type Ref } from 'vue'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'
import { perfMark } from '@/utils/perf'

export const queryFieldSeparator = ';'
export const queryKeyValueSeparator = ':'

// Charts read the active filter query through provide/inject rather than a prop.
// A prop change re-renders every chart on each filter tick (their heaviest work
// is i18n + option rebuild); injecting keeps `query` off their prop list, so the
// dashboard's re-render skips the charts and they update only via their own
// (staggered) counts. See useDashboard's provide below.
export const dashboardQueryKey: InjectionKey<Ref<string | undefined>> = Symbol('dashboardQuery')

/**
 * The committed query with `field`'s clause replaced by `value` (or removed when
 * undefined): what a brush publishes as a live frame mid-drag, so the frame
 * filters by the drag *plus* every already-applied filter (see crossfilterBus).
 */
export function withFieldClause(
  query: string | undefined,
  field: string,
  value?: string
): string | undefined {
  const base = query ? query.split(queryFieldSeparator) : []
  const clauses = base.filter((clause) => !clause.startsWith(field + queryKeyValueSeparator))
  if (value) clauses.push(`${field}${queryKeyValueSeparator}${value}`)
  return clauses.length ? clauses.join(queryFieldSeparator) : undefined
}

export function useDashboard<M>(
  route: RouteLocationNormalizedLoaded,
  router: Router,
  field: object
) {
  const fields: string[] = Object.values(field)
  // URL keys accepted back into `searches`: the component's own fields, plus
  // derived-ratio keys (`a/b`, both sides known) written by parallel-chart
  // brushes on division axes.
  function isKnownKey(key: string): boolean {
    if (fields.includes(key)) return true
    if (!key.includes('/')) return false
    const parts = key.split('/', 2)
    return parts.length === 2 && parts.every((part) => fields.includes(part))
  }

  const search = ref<string>('')
  const searches = ref<Searches>({})
  const item = ref<M>()
  const detail = ref<boolean>(false)

  function clickTableRow(value: M): void {
    item.value = value
  }
  function closeDetail(): void {
    item.value = undefined
  }
  function updatePage(page: Page<M>): void {
    if (detail.value && page.total === 1) {
      item.value = page.items[0]
      detail.value = false
    }
  }
  function changeSearches(key: string, value?: Value): void {
    if (value) {
      searches.value[key] = value
    } else {
      delete searches.value[key]
    }
    triggerRef(searches)
    // Benchmark (#354): the start of a filter interaction. Everything the
    // charts and the table then do is downstream of this one mark.
    perfMark('query:commit', { key })
  }

  const query = computed<string>(() => {
    const queries = Object.entries(searches.value)
      .filter(([, value]) => filterColumnValue(value))
      .map(([key, value]) => `${key}${queryKeyValueSeparator}${value}`)
    const searchValue = unref(search)
    if (searchValue && searchValue.length > 0) {
      queries.push(`%${searchValue}%`)
    }
    return queries.join(queryFieldSeparator)
  })

  // Expose query to descendant charts without prop-drilling (see dashboardQueryKey).
  provide(dashboardQueryKey, query)

  // Mirror the filter state into the URL, but debounced and via replace (not
  // push): a slider drag mutates searches on every tick, which previously fired
  // an un-debounced router.push per tick — flooding the history stack and
  // re-running the route.query → searches write-back below each time. Debouncing
  // coalesces a drag into a single navigation; replace keeps the back button
  // returning to the pre-filter view instead of stepping through every tick.
  const syncQueryToRouter = debounce(() => {
    if (!router) return
    const query = {
      ...searches.value,
      ...(search.value ? { [globalSearchKey]: search.value } : {})
    }
    router.replace({ query })
  }, debounceAPITime)

  watch(() => [searches.value, search.value], syncQueryToRouter, {
    immediate: true,
    deep: true
  })

  watch(
    () => route.query,
    (newQuery) => {
      // Update or add keys from newQuery
      Object.entries(newQuery)
        .filter(([key]) => isKnownKey(key))
        .forEach(([key, value]) => {
          const newValue = parseValue(value)
          if (newValue !== undefined) {
            // Update the value if changed or add it if not present
            if (JSON.stringify(searches.value[key]) !== JSON.stringify(newValue)) {
              searches.value[key] = newValue
            }
          } else {
            // Remove the key if the new value is invalid
            delete searches.value[key]
          }
        })

      // Remove keys that are in searches.value but not in newQuery
      Object.keys(searches.value).forEach((key) => {
        if (!(key in newQuery)) {
          delete searches.value[key]
        }
      })
    },
    { immediate: true, deep: true }
  )

  const globalSearchValue = route.query[globalSearchKey]
  if (typeof globalSearchValue === 'string') {
    search.value = globalSearchValue
  }
  const detailValue = route.query['detail']
  if (detailValue && typeof detailValue === 'string' && detailValue.toLowerCase() === 'true') {
    detail.value = true
  }

  return {
    search,
    searches,
    item,
    query,
    clickTableRow,
    closeDetail,
    updatePage,
    changeSearches
  }
}

function parseValue(value: string | null | (string | null)[]): Value | undefined {
  if (value === null) {
    return undefined
  }
  if (typeof value === 'string') {
    if (value.includes(',')) {
      return value.split(',')
    }
    if (value === 'true') {
      return true
    }
    if (value === 'false') {
      return false
    }
    const numberValue = Number(value)
    if (!isNaN(numberValue)) {
      return numberValue
    }
    return value
  } else {
    return value.filter((v) => v !== null)
  }
}
