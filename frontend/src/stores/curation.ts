/**
 * Curation (review) state: the open-submission queue and per-PR details,
 * projected by the backend from the data repository's pull requests.
 *
 * Everything is fetch-once per session (the backend adds its own TTL caches on
 * top): back-navigating between the queue and a review screen must not re-hit
 * the GitHub-backed endpoints.
 */

import type { CurationComment, CurationDetail, CurationSummary } from '@/backend'
import type { ValidationResponse } from '@/utils/validationResponse'
import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * The API client, imported once and shared.
 *
 * Lazy, to keep axios out of the entry bundle (see stores/counts.ts), but not
 * once per call: loading a submission asks for several files at a time, and
 * firing a dynamic import per call resolves the module over and over.
 */
let apiModule: Promise<typeof import('@/plugins/axios')> | null = null
function api(): Promise<typeof import('@/plugins/axios')> {
  apiModule ??= import('@/plugins/axios')
  return apiModule
}

export const useCurationStore = defineStore('curation', () => {
  const items = ref<CurationSummary[]>([])
  const configured = ref(true)
  const listState = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')

  const details = ref(new Map<number, CurationDetail>())
  const validations = ref(new Map<number, ValidationResponse>())
  const fileTexts = ref(new Map<string, string>())
  const comments = ref(new Map<number, CurationComment[]>())

  async function fetchList(force = false): Promise<void> {
    if (listState.value === 'loading' || (listState.value === 'ready' && !force)) return
    listState.value = 'loading'
    try {
      const { defaultApi } = await api()
      // force: the Refresh button, so skip the server cache too (#267).
      const { data } = await defaultApi.listContributions(force)
      configured.value = data.configured
      items.value = data.items ?? []
      listState.value = 'ready'
    } catch {
      listState.value = 'error'
    }
  }

  async function fetchDetail(prNumber: number): Promise<CurationDetail> {
    const cached = details.value.get(prNumber)
    if (cached) return cached
    const { defaultApi } = await api()
    const { data } = await defaultApi.getContribution(prNumber)
    details.value.set(prNumber, data)
    return data
  }

  async function fetchValidation(prNumber: number): Promise<ValidationResponse> {
    const cached = validations.value.get(prNumber)
    if (cached) return cached
    const { defaultApi } = await api()
    const { data } = await defaultApi.getContributionValidation(prNumber)
    const response = data as unknown as ValidationResponse
    validations.value.set(prNumber, response)
    return response
  }

  /**
   * The submission's discussion. Unlike the rest of the curation state this
   * one moves while a curator is on the page (someone replies on GitHub), so
   * `force` skips the cache for the panel's refresh button.
   */
  async function fetchComments(prNumber: number, force = false): Promise<CurationComment[]> {
    const cached = comments.value.get(prNumber)
    if (cached && !force) return cached
    const { defaultApi } = await api()
    const { data } = await defaultApi.getContributionComments(prNumber)
    comments.value.set(prNumber, data.items)
    return data.items
  }

  async function fetchFileText(prNumber: number, path: string): Promise<string> {
    const key = `${prNumber}:${path}`
    const cached = fileTexts.value.get(key)
    if (cached !== undefined) return cached
    const { defaultApi } = await api()
    const { data } = await defaultApi.getContributionFile(prNumber, path)
    fileTexts.value.set(key, data)
    return data
  }

  /**
   * Forget everything cached about one submission.
   *
   * Called after the editor pushes an update: what is held here still
   * describes the commit that was just replaced, so reloading the edit page
   * on it would send a stale head sha and collide.
   */
  function invalidate(prNumber: number): void {
    details.value.delete(prNumber)
    validations.value.delete(prNumber)
    comments.value.delete(prNumber)
    for (const key of [...fileTexts.value.keys()]) {
      if (key.startsWith(`${prNumber}:`)) fileTexts.value.delete(key)
    }
  }

  return {
    invalidate,
    items,
    configured,
    listState,
    details,
    fetchList,
    fetchDetail,
    fetchValidation,
    fetchFileText,
    fetchComments
  }
})
