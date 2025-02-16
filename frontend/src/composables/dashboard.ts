import type { Page } from '@/utils/backend'
import { filterColumnValue, globalSearchKey, type Searches, type Value } from '@/utils/common'
import { computed, ref, triggerRef, unref, watch } from 'vue'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'

export const queryFieldSeparator = ';'
export const queryKeyValueSeparator = ':'

export function useDashboard<M>(
  route: RouteLocationNormalizedLoaded,
  router: Router,
  field: object
) {
  const fields: string[] = Object.values(field)

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

  watch(
    () => [searches.value, search.value],
    () => {
      const query = {
        ...searches.value,
        ...(search.value ? { [globalSearchKey]: search.value } : {})
      }
      if (router) {
        router.push({ query })
      }
    },
    { immediate: true, deep: true }
  )

  watch(
    () => route.query,
    (newQuery) => {
      // Update or add keys from newQuery
      Object.entries(newQuery)
        .filter(([key, value]) => fields.includes(key))
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
