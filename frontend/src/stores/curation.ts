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
      const { defaultApi } = await import('@/plugins/axios')
      const { data } = await defaultApi.listContributions()
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
    const { defaultApi } = await import('@/plugins/axios')
    const { data } = await defaultApi.getContribution(prNumber)
    details.value.set(prNumber, data)
    return data
  }

  async function fetchValidation(prNumber: number): Promise<ValidationResponse> {
    const cached = validations.value.get(prNumber)
    if (cached) return cached
    const { defaultApi } = await import('@/plugins/axios')
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
    const { defaultApi } = await import('@/plugins/axios')
    const { data } = await defaultApi.getContributionComments(prNumber)
    comments.value.set(prNumber, data.items)
    return data.items
  }

  async function fetchFileText(prNumber: number, path: string): Promise<string> {
    const key = `${prNumber}:${path}`
    const cached = fileTexts.value.get(key)
    if (cached !== undefined) return cached
    const { defaultApi } = await import('@/plugins/axios')
    const { data } = await defaultApi.getContributionFile(prNumber, path)
    fileTexts.value.set(key, data)
    return data
  }

  return {
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
