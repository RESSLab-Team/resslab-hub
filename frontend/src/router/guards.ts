/**
 * Who may open which route (#247).
 *
 * The decision is a pure function of the route's meta, the signed-in user and
 * whether the deployment offers contributions, so it can be tested without a
 * router or a browser. `installAuthGuard` is the thin wiring around it.
 */

import { rankOf, useAuthStore, type Role } from '@/stores/auth'
import { useFeaturesStore } from '@/stores/features'
import type { RouteLocationNormalized, RouteLocationRaw, Router } from 'vue-router'

export interface GuardUser {
  role?: string
}

/**
 * `true` to let the navigation through, or where to send it instead.
 *
 * A route with `meta.contributions` belongs to the contribution pipeline: on
 * a deployment that switched it off (`CONTRIBUTIONS_ENABLED=false`), it goes
 * home, before anyone is asked to sign in.
 *
 * A visitor who is not signed in goes to the sign-in page, with where they
 * were headed, so they land there afterwards. Someone signed in whose role is
 * too low goes to a page that says so, because sending them back to sign in
 * would suggest signing in again would help.
 */
export function resolveGuard(
  to: RouteLocationNormalized,
  user: GuardUser | null,
  contributionsEnabled: boolean
): true | RouteLocationRaw {
  if (to.meta?.contributions && !contributionsEnabled) {
    return { path: '/', replace: true }
  }
  const required = to.meta?.auth as Role | undefined
  if (!required) return true
  if (!user) {
    return { name: 'Login', query: { next: to.fullPath } }
  }
  if (rankOf(user.role ?? 'viewer') < rankOf(required)) {
    return { name: 'Forbidden', query: { next: to.fullPath, need: required } }
  }
  return true
}

export function installAuthGuard(router: Router): void {
  router.beforeEach(async (to) => {
    // Only these routes wait on the backend. Browsing the databases stays
    // account-free, and must not pay a round trip to find that out.
    if (!to.meta?.auth && !to.meta?.contributions) return true
    const features = useFeaturesStore()
    await features.ensureLoaded()
    const enabled = features.contributions !== false
    // Switched off: no need to ask who is signed in, nobody can be.
    if (to.meta?.auth && enabled) await useAuthStore().ensureLoaded()
    return resolveGuard(to, useAuthStore().user, enabled)
  })
}
