/**
 * Who may open which route (#247).
 *
 * The decision is a pure function of the route's `meta.auth` and the signed-in
 * user, so it can be tested without a router or a browser. `installAuthGuard`
 * is the thin wiring around it.
 */

import { rankOf, useAuthStore, type Role } from '@/stores/auth'
import type { RouteLocationNormalized, RouteLocationRaw, Router } from 'vue-router'

export interface GuardUser {
  role?: string
}

/**
 * `true` to let the navigation through, or where to send it instead.
 *
 * A visitor who is not signed in goes to the sign-in page, with where they
 * were headed, so they land there afterwards. Someone signed in whose role is
 * too low goes to a page that says so, because sending them back to sign in
 * would suggest signing in again would help.
 */
export function resolveGuard(
  to: RouteLocationNormalized,
  user: GuardUser | null
): true | RouteLocationRaw {
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
    // Only guarded routes wait on the backend. Browsing the databases stays
    // account-free, and must not pay a round trip to find that out.
    if (!to.meta?.auth) return true
    const auth = useAuthStore()
    await auth.ensureLoaded()
    return resolveGuard(to, auth.user)
  })
}
