import type { CountModel } from '@/backend'
import type { Page } from '@/utils/backend'
import type { Searches } from '@/utils/common'
import { debounceAPIParameters, debounceAPITime } from '@/utils/common'
import type { DataOptions } from '@/utils/vuetify'
import type { AxiosResponse } from 'axios'
import download from 'downloadjs'
import JSZip from 'jszip'
import { debounce } from 'lodash'
import { computed, onScopeDispose, ref, shallowRef, unref, watch, type Ref } from 'vue'
import { subscribeCrossfilter } from './crossfilterBus'
import { cancelScheduled, scheduleFrameUpdate } from './frameScheduler'

// Unique per table instance for the frame scheduler's latest-wins coalescing.
let tableInstanceId = 0

export enum DownloadType {
  Main = 'main',
  Test = 'test'
}

export type ColumnType = 'text' | 'option' | 'number' | 'boolean'

export interface Column {
  value: string
  type: ColumnType
  title?: string
  options?: string[]
  filterOnly?: boolean
  format?: (value: any) => string
  /** Design-system cell treatment: monospace section names, tag pill, bold identifier */
  cellVariant?: 'mono' | 'tag' | 'strong'
}

export const tableProps = {
  query: String,
  search: String,
  searches: {
    type: Object as () => Searches,
    default: () => ({})
  }
}
export interface TableEmits<M> {
  (e: 'click:row', value: M): void
  (e: 'update:page', value: Page<M>): void
  (e: 'update:search', value: string | undefined): void
  (e: 'update:searches', value: Searches): void
}
export function useTable<M extends { id: string }, P extends Page<M> = Page<M>>(
  emit: TableEmits<M>,
  name: string,
  query: Ref<string | undefined>,
  searchRef: Ref<string | undefined>,
  searchesRef: Ref<Searches>,
  tests: {
    name: string
    countKey: keyof M
    getCsv: (id: string) => Promise<AxiosResponse>
  }[],
  getCounts: () => Promise<AxiosResponse<CountModel[]>>,
  getPage: (
    query?: string,
    sortBy?: Array<string>,
    sortDesc?: Array<boolean>,
    page?: number,
    size?: number
  ) => Promise<AxiosResponse<P>>,
  getMainCsv: (ids: string[]) => Promise<AxiosResponse>,
  notify: (message: string) => void,
  // Optional crossfilter drag source (the sync half of useDataset). When given,
  // a brush drag streams the current page live from the in-memory dataset into
  // `liveItems`/`liveCount` — display-only overlays for SimpleTable; pagination
  // keeps riding the committed totalFilteredCount. Both clear on pointer-up.
  live?: {
    countRowsSync: (query?: string) => number
    pageSync: (
      query?: string,
      sortBy?: string[],
      sortDesc?: boolean[],
      page?: number,
      size?: number
    ) => M[]
  }
) {
  const loading = ref<boolean>(false)
  // shallowRef: rows are replaced wholesale each page and each ConnectionModel
  // carries ~100 fields — deep reactivity would proxy-wrap every field, which
  // Vuetify's transformItems then pays a getter tax on for every cell. The rows
  // are read-only here, so a shallow ref keeps them as plain objects.
  const items = shallowRef<M[]>([])
  const updateKey = `table-${tableInstanceId++}`
  const options = ref<DataOptions>()
  const totalCount = ref<number>()
  const totalFilteredCount = ref<number>()

  const search = computed<string | undefined>({
    get: () => searchRef.value,
    set: (value) => emit('update:search', value)
  })
  const searches = computed<Searches>({
    get: () => searchesRef.value,
    set: (value) => emit('update:searches', value)
  })

  function clickRow(item: M) {
    emit('click:row', item)
  }
  function downloadFiles(items: M[], types: DownloadType[]): void {
    const filePromises = [
      types.includes(DownloadType.Main)
        ? [
            getMainCsv(items.map((item) => item.id)).then((response) => ({
              filename: `${name}.csv`,
              content: response.data
            }))
          ]
        : [],
      types.includes(DownloadType.Test)
        ? tests.flatMap((test) =>
            items
              .filter((item) => (item[test.countKey] as unknown as number) > 0)
              .map((item) => item.id)
              .map((id) =>
                test.getCsv(id).then((response) => ({
                  filename: `${name}-${test.name}-${id}.csv`,
                  content: response.data
                }))
              )
          )
        : []
    ].flat()
    Promise.all(filePromises)
      .then((files) => {
        if (files.length === 0) {
          notify('Nothing to download')
          return null
        }
        const zip = new JSZip()
        files.forEach((file) => {
          zip.file(file.filename, file.content)
        })
        return zip.generateAsync({ type: 'blob' })
      })
      .then((content) => {
        if (content) {
          download(content, `export-${new Date().getTime()}.zip`, 'application/zip')
        }
      })
      .catch((error) => {
        notify(`An error occured : ${error}`)
      })
  }

  getCounts()
    .then((response) => response.data)
    .then((counts) => {
      totalCount.value = counts[0].value
    })

  const debouncedGetPage = debounce(
    () => {
      const optionsValue = unref(options)
      if (optionsValue) {
        loading.value = true
        getPage(
          query.value,
          optionsValue.sortBy?.map((sortBy) => sortBy.key),
          optionsValue.sortBy?.map((sortBy) => sortBy.order === 'desc'),
          optionsValue.page,
          optionsValue.itemsPerPage === -1 ? 1000 : optionsValue.itemsPerPage
        )
          .then((response) => response.data)
          .then((page) => {
            // Stagger the write so the table doesn't share a flush with the
            // charts (all recompute on the same filter change).
            scheduleFrameUpdate(updateKey, () => {
              items.value = page.items
              totalFilteredCount.value = page.total || 0
              emit('update:page', page)
            })
          })
          .finally(() => {
            loading.value = false
          })
      }
    },
    debounceAPITime,
    debounceAPIParameters
  )
  // A trailing debounce fire or queued frame task must not write refs of a
  // disposed component.
  onScopeDispose(() => {
    debouncedGetPage.cancel()
    cancelScheduled(updateKey)
  })

  watch(() => [query.value, options], debouncedGetPage, { immediate: true, deep: true })

  // Live crossfilter rows: the light-DOM virtualized body re-renders its visible
  // rows in a few ms, so the table can track a drag frame-for-frame like the charts.
  const liveCount = ref<number>()
  const liveItems = shallowRef<M[]>()
  if (live) {
    const unsubscribe = subscribeCrossfilter({
      onLive: (liveQuery) => {
        liveCount.value = live.countRowsSync(liveQuery)
        const opts = options.value
        liveItems.value = live.pageSync(
          liveQuery,
          opts?.sortBy?.map((sort) => sort.key),
          opts?.sortBy?.map((sort) => sort.order === 'desc'),
          opts?.page,
          opts?.itemsPerPage === -1 ? 1000 : opts?.itemsPerPage
        )
      },
      onSettle: () => {
        liveCount.value = undefined
        liveItems.value = undefined
      }
    })
    onScopeDispose(unsubscribe)
  }

  return {
    items,
    loading,
    options,
    totalCount,
    totalFilteredCount,
    search,
    searches,
    clickRow,
    downloadFiles,
    liveCount,
    liveItems
  }
}
