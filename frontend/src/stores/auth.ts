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

// Loaded lazily, and once: the axios plugin imports this store back for its
// 401 interceptor, and one shared promise keeps concurrent calls on the same
// module instance (which the unit tests mock).
let apiModule: Promise<typeof import('@/plugins/axios')> | null = null
function api() {
  apiModule ??= import('@/plugins/axios')
  return apiModule
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
  const hasOrcid = computed(() =>
    identities.value.some((identity) => identity.provider === 'orcid')
  )
  /** Every verified address of the account (#402). The main one is `user.email`. */
  const emails = computed<IdentityOut[]>(() =>
    identities.value.filter((identity) => identity.provider === 'email')
  )
  const mainEmail = computed(() => user.value?.email ?? null)

  function hasRole(minimum: Role): boolean {
    return !!user.value && rankOf(user.value.role ?? 'viewer') >= rankOf(minimum)
  }

  function clear(): void {
    user.value = null
    status.value = 'anonymous'
  }

  async function ensureLoaded(force = false): Promise<void> {
    if (inFlight) return inFlight
    if (!force && status.value !== 'unknown') return
    inFlight = (async () => {
      try {
        const { authApi } = await api()
        const { data } = await authApi.getMe()
        user.value = data.user ?? null
        status.value = data.user ? 'authenticated' : 'anonymous'
      } catch {
        // A network or server failure must not lock the app: treat it as not
        // signed in, and the next navigation asks again.
        clear()
      } finally {
        inFlight = null
      }
    })()
    return inFlight
  }

  /** Mail a sign-in code. Always resolves, whatever the address. */
  async function startEmailLogin(email: string, redirectTo = '/'): Promise<void> {
    const { authApi } = await api()
    await authApi.startEmailLogin({ email, redirect_to: redirectTo })
  }

  /** Finish with the typed code, or with the pair from the mailed link. */
  async function verifyEmailLogin(payload: {
    code?: string
    challenge?: string
    token?: string
  }): Promise<string> {
    const { authApi } = await api()
    const { data } = await authApi.verifyEmailLogin(payload)
    user.value = data.user
    status.value = 'authenticated'
    return data.redirect_to || '/'
  }

  /**
   * Leave the app for an OAuth provider. A full navigation, not a fetch: the
   * round trip has to happen in the address bar for the cookies to travel
   * with it.
   */
  async function goToProvider(
    provider: 'github' | 'orcid',
    options: { redirectTo?: string; link?: boolean }
  ): Promise<void> {
    const { baseUrl } = await api()
    const query = new URLSearchParams({ redirect_to: options.redirectTo ?? '/' })
    if (options.link) query.set('link', 'true')
    window.location.assign(`${baseUrl}/auth/${provider}/start?${query.toString()}`)
  }

  const goToGitHub = (options: { redirectTo?: string; link?: boolean } = {}) =>
    goToProvider('github', options)
  const goToOrcid = (options: { redirectTo?: string; link?: boolean } = {}) =>
    goToProvider('orcid', options)

  async function logout(): Promise<void> {
    const { authApi } = await api()
    try {
      await authApi.logout()
    } finally {
      clear()
    }
  }

  async function unlinkIdentity(id: string): Promise<void> {
    const { authApi } = await api()
    await authApi.deleteIdentity(id)
    await ensureLoaded(true)
  }

  /**
   * Mail a code to an address to add to this account (#402). Code only, no
   * link: it must be typed here, in the session that asked.
   */
  async function startAddEmail(email: string): Promise<void> {
    const { authApi } = await api()
    await authApi.startAddEmail({ email })
  }

  /**
   * Add the address with the typed code. The answer is the updated account.
   *
   * True when it is another account: this one had only an ORCID iD or a
   * GitHub login, the address belongs to an existing account, and the two
   * joined there (#250). The browser is signed in to that account now.
   */
  async function verifyAddEmail(code: string): Promise<boolean> {
    const { authApi } = await api()
    const before = user.value?.id
    const { data } = await authApi.verifyAddEmail({ code })
    user.value = data
    status.value = 'authenticated'
    return !!before && before !== data.id
  }

  /** Make one of the account's addresses the main one. */
  async function setMainEmail(identityId: string): Promise<void> {
    const { authApi } = await api()
    await authApi.setMainEmail(identityId)
    await ensureLoaded(true)
  }

  /**
   * Ask the admins for the contributor role (#248). The answer comes back on
   * `user.access_request`, so the page shows it waiting.
   */
  async function requestAccess(message: string): Promise<void> {
    const { authApi } = await api()
    const { data } = await authApi.requestAccess({ message })
    if (user.value) user.value = { ...user.value, access_request: data }
  }

  return {
    user,
    status,
    isAuthenticated,
    identities,
    hasGitHub,
    hasOrcid,
    emails,
    mainEmail,
    hasRole,
    clear,
    ensureLoaded,
    startEmailLogin,
    verifyEmailLogin,
    goToGitHub,
    goToOrcid,
    logout,
    unlinkIdentity,
    startAddEmail,
    verifyAddEmail,
    setMainEmail,
    requestAccess
  }
})
