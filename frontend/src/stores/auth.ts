import { LocalStorageKey } from '@/utils/localStorage'
import { defineStore } from 'pinia'

export type SignInMethod = 'tequila' | 'edugain' | 'orcid' | 'email'

interface State {
  signedIn: boolean
  email: string
  method: SignInMethod | null
}

const SIGNED_OUT: State = { signedIn: false, email: '', method: null }

/**
 * Placeholder session for the contribution pipeline.
 *
 * There is no identity provider behind this yet: any sign-in action is
 * accepted, and the "session" is a localStorage entry so a page reload does not
 * drop you back at the gate. Replace wholesale once real SSO lands.
 */
function restore(): State {
  const stored = localStorage.getItem(LocalStorageKey.Auth)
  if (!stored) return { ...SIGNED_OUT }
  try {
    const parsed = JSON.parse(stored) as Partial<State>
    return parsed.signedIn
      ? { signedIn: true, email: parsed.email ?? '', method: parsed.method ?? null }
      : { ...SIGNED_OUT }
  } catch {
    return { ...SIGNED_OUT }
  }
}

export const useAuthStore = defineStore('auth', {
  state: restore,
  actions: {
    signIn(method: SignInMethod, email = '') {
      this.signedIn = true
      this.method = method
      this.email = email
      localStorage.setItem(LocalStorageKey.Auth, JSON.stringify(this.$state))
    },
    signOut() {
      this.$patch({ ...SIGNED_OUT })
      localStorage.removeItem(LocalStorageKey.Auth)
    }
  }
})
