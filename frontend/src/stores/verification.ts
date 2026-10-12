/**
 * Verification state (#253): the unverified rows waiting for a curator, and
 * the "Mark as verified" button that opens their pull request on the data
 * repository. Curators only, the backend answers 403 to anyone else.
 *
 * The list comes from the database, so a verification merged on GitHub stays
 * in it until the next upload. The store keeps the pull requests it opened in
 * this session, so the button turns into "Pending" at once instead of waiting
 * for a refresh.
 */

import type { VerificationGroup, VerificationPull } from '@/backend'
import type { Type } from '@/backend'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

// Lazy and shared, like the other stores (see stores/curation.ts).
let apiModule: Promise<typeof import('@/plugins/axios')> | null = null
function api(): Promise<typeof import('@/plugins/axios')> {
  apiModule ??= import('@/plugins/axios')
  return apiModule
}

/** The sentence the backend sent in `detail` (a 409 names the ids), if any. */
export function errorDetail(caught: unknown): string | undefined {
  const detail = (caught as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : undefined
}

function key(database: string, id: string): string {
  return `${database}\u0000${id}`
}

export const useVerificationStore = defineStore('verification', () => {
  const groups = ref<VerificationGroup[]>([])
  const configured = ref(true)
  const listState = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')
  /** Pull requests opened from this tab, by database and id. */
  const opened = ref(new Map<string, VerificationPull>())

  /** Every pending pull request, by database and id: the list's, then ours. */
  const pending = computed(() => {
    const byRow = new Map<string, VerificationPull>()
    for (const group of groups.value) {
      if (!group.pending_pr) continue
      for (const id of group.ids) byRow.set(key(group.database, id), group.pending_pr)
    }
    for (const [row, pull] of opened.value) byRow.set(row, pull)
    return byRow
  })

  const unverifiedCount = computed(() =>
    groups.value.reduce((total, group) => total + group.count, 0)
  )

  async function fetchList(force = false): Promise<void> {
    if (listState.value === 'loading' || (listState.value === 'ready' && !force)) return
    listState.value = 'loading'
    try {
      const { defaultApi } = await api()
      const { data } = await defaultApi.listUnverified()
      configured.value = data.configured
      groups.value = data.groups ?? []
      listState.value = 'ready'
    } catch {
      listState.value = 'error'
    }
  }

  /** The open verification pull request that covers this row, if any. */
  function pendingFor(database: string, id: string): VerificationPull | undefined {
    return pending.value.get(key(database, id))
  }

  /** Open the pull request. Throws the API error, the caller shows it. */
  async function verify(database: Type, ids: string[]): Promise<VerificationPull> {
    const { defaultApi } = await api()
    const { data } = await defaultApi.createVerification({ database, ids })
    const pull: VerificationPull = { pr_number: data.pr_number, pr_url: data.pr_url }
    const next = new Map(opened.value)
    for (const id of ids) next.set(key(database, id), pull)
    opened.value = next
    return pull
  }

  return {
    groups,
    configured,
    listState,
    unverifiedCount,
    fetchList,
    pendingFor,
    verify
  }
})
