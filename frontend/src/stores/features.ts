/**
 * What this deployment offers, from `GET /features`.
 *
 * Read at runtime and not from a `VITE_` variable on purpose: stage and prod
 * run the same image, and prod switches the contribution pipeline off with
 * `CONTRIBUTIONS_ENABLED=false` in its backend ConfigMap (docs/releasing.md).
 * Asked once per page load, by the sidebar and by the router guard.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

// Same lazy, shared import as the auth store: the axios plugin imports the
// auth store back, and one promise keeps every call on the module the unit
// tests mock.
let apiModule: Promise<typeof import('@/plugins/axios')> | null = null
function api() {
  apiModule ??= import('@/plugins/axios')
  return apiModule
}

export const useFeaturesStore = defineStore('features', () => {
  /** Submit, curation, sign-in and account. `null` until the answer is in. */
  const contributions = ref<boolean | null>(null)

  let inFlight: Promise<void> | null = null

  async function ensureLoaded(): Promise<void> {
    if (inFlight) return inFlight
    if (contributions.value !== null) return
    inFlight = (async () => {
      try {
        const { defaultApi } = await api()
        const { data } = await defaultApi.getFeatures()
        contributions.value = data.contributions
      } catch {
        // Backend down or slow: every link fails anyway, but a passing error
        // must not hide sign-in for the rest of the visit. On a deployment
        // that switched it off, the endpoints still answer 404.
        contributions.value = true
      } finally {
        inFlight = null
      }
    })()
    return inFlight
  }

  return { contributions, ensureLoaded }
})
