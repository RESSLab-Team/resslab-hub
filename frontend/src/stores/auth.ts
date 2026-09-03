/**
 * Who is signed in (#247).
 *
 * Browsing needs no account, so this store starts as `unknown` and only asks
 * the backend when something depends on the answer: a guarded route, or the
 * account block in the sidebar. The session itself is an httpOnly cookie the
 * browser attaches on its own, so nothing here holds a credential.
 */

import type { IdentityOut, UserOut } from '@/backend'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

/** Weakest first: everything a role can do, a stronger one can do too. */
export const ROLE_ORDER = ['viewer', 'contributor', 'curator', 'admin'] as const
export type Role = (typeof ROLE_ORDER)[number]

export function rankOf(role: string): number {
  const index = ROLE_ORDER.indexOf(role as Role)
  return index < 0 ? 0 : index
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserOut | null>(null)
  const status = ref<'unknown' | 'anonymous' | 'authenticated'>('unknown')

  // One request even if several guards and components ask at once.
  let inFlight: Promise<void> | null = null

  const isAuthenticated = computed(() => status.value === 'authenticated')
  const identities = computed<IdentityOut[]>(() => user.value?.identities ?? [])
  const hasGitHub = computed(() =>
    identities.value.some((identity) => identity.provider === 'github')
  )

  function hasRole(minimum: Role): boolean {
    return !!user.value && rankOf(user.value.role ?? 'viewer') >= rankOf(minimum)
  }

  function clear(): void {
    user.value = null
    status.value = 'anonymous'
    inFlight = null
  }

  async function ensureLoaded(force = false): Promise<void> {
    if (!force && status.value !== 'unknown') return
    if (inFlight && !force) return inFlight
    inFlight = (async () => {
      try {
        const { authApi } = await import('@/plugins/axios')
        const { data } = await authApi.getMe()
        user.value = data.user ?? null
        status.value = data.user ? 'authenticated' : 'anonymous'
      } catch {
        // A network or server failure must not lock the app: treat it as not
        // signed in, and the next navigation asks again.
        user.value = null
        status.value = 'anonymous'
      } finally {
        inFlight = null
      }
    })()
    return inFlight
  }

  /** Mail a sign-in code. Always resolves, whatever the address. */
  async function startEmailLogin(email: string, redirectTo = '/'): Promise<void> {
    const { authApi } = await import('@/plugins/axios')
    await authApi.startEmailLogin({ email, redirect_to: redirectTo })
  }

  /** Finish with the typed code, or with the pair from the mailed link. */
  async function verifyEmailLogin(payload: {
    code?: string
    challenge?: string
    token?: string
  }): Promise<string> {
    const { authApi } = await import('@/plugins/axios')
    const { data } = await authApi.verifyEmailLogin(payload)
    user.value = data.user
    status.value = 'authenticated'
    return data.redirect_to || '/'
  }

  /**
   * Leave the app for GitHub. A full navigation, not a fetch: the OAuth round
   * trip has to happen in the address bar for the cookies to travel with it.
   */
  function goToGitHub(options: { redirectTo?: string; link?: boolean } = {}): void {
    const { baseUrl } = { baseUrl: import.meta.env.VITE_APP_BACKEND_URL }
    const query = new URLSearchParams({ redirect_to: options.redirectTo ?? '/' })
    if (options.link) query.set('link', 'true')
    window.location.assign(`${baseUrl}/auth/github/start?${query.toString()}`)
  }

  async function logout(): Promise<void> {
    const { authApi } = await import('@/plugins/axios')
    try {
      await authApi.logout()
    } finally {
      clear()
    }
  }

  async function unlinkIdentity(id: string): Promise<void> {
    const { authApi } = await import('@/plugins/axios')
    await authApi.deleteIdentity(id)
    await ensureLoaded(true)
  }

  return {
    user,
    status,
    isAuthenticated,
    identities,
    hasGitHub,
    hasRole,
    clear,
    ensureLoaded,
    startEmailLogin,
    verifyEmailLogin,
    goToGitHub,
    logout,
    unlinkIdentity
  }
})
