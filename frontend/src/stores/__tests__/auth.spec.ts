import { useAuthStore } from '@/stores/auth'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMe = vi.fn()
const logout = vi.fn()
const startEmailLogin = vi.fn()
const verifyEmailLogin = vi.fn()
const deleteIdentity = vi.fn()
const requestAccess = vi.fn()
const startAddEmail = vi.fn()
const verifyAddEmail = vi.fn()
const setMainEmail = vi.fn()

vi.mock('@/plugins/axios', () => ({
  baseUrl: '/api',
  authApi: {
    getMe: (...args: unknown[]) => getMe(...args),
    logout: (...args: unknown[]) => logout(...args),
    startEmailLogin: (...args: unknown[]) => startEmailLogin(...args),
    verifyEmailLogin: (...args: unknown[]) => verifyEmailLogin(...args),
    deleteIdentity: (...args: unknown[]) => deleteIdentity(...args),
    requestAccess: (...args: unknown[]) => requestAccess(...args),
    startAddEmail: (...args: unknown[]) => startAddEmail(...args),
    verifyAddEmail: (...args: unknown[]) => verifyAddEmail(...args),
    setMainEmail: (...args: unknown[]) => setMainEmail(...args)
  }
}))

const ADA = {
  id: 'u1',
  email: 'ada@example.edu',
  email_verified: true,
  display_name: 'Ada Lovelace',
  institution: 'EPFL',
  role: 'curator',
  role_source: 'default',
  github_login: 'ada',
  identities: [
    { id: 'i1', provider: 'email', handle: 'ada@example.edu' },
    { id: 'i2', provider: 'github', handle: 'ada' }
  ]
}

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('starts out not knowing, and asks only once', async () => {
    getMe.mockResolvedValue({ data: { user: ADA } })
    const store = useAuthStore()
    expect(store.status).toBe('unknown')

    await Promise.all([store.ensureLoaded(), store.ensureLoaded()])
    await store.ensureLoaded()

    expect(getMe).toHaveBeenCalledTimes(1)
    expect(store.status).toBe('authenticated')
    expect(store.user?.email).toBe('ada@example.edu')
  })

  it('reads a null user as anonymous, not as an error', async () => {
    getMe.mockResolvedValue({ data: { user: null } })
    const store = useAuthStore()
    await store.ensureLoaded()
    expect(store.status).toBe('anonymous')
    expect(store.isAuthenticated).toBe(false)
  })

  it('does not lock the app when the request fails', async () => {
    getMe.mockRejectedValue(new Error('offline'))
    const store = useAuthStore()
    await store.ensureLoaded()
    expect(store.status).toBe('anonymous')
    expect(store.user).toBeNull()
  })

  it('compares roles by strength', async () => {
    getMe.mockResolvedValue({ data: { user: ADA } })
    const store = useAuthStore()
    await store.ensureLoaded()
    expect(store.hasRole('viewer')).toBe(true)
    expect(store.hasRole('curator')).toBe(true)
    expect(store.hasRole('admin')).toBe(false)
  })

  it('has no role at all when nobody is signed in', () => {
    const store = useAuthStore()
    expect(store.hasRole('viewer')).toBe(false)
  })

  it('sees the linked GitHub identity', async () => {
    getMe.mockResolvedValue({ data: { user: ADA } })
    const store = useAuthStore()
    await store.ensureLoaded()
    expect(store.hasGitHub).toBe(true)
    expect(store.identities).toHaveLength(2)
  })

  it('sees a linked ORCID iD', async () => {
    getMe.mockResolvedValue({ data: { user: ADA } })
    const store = useAuthStore()
    await store.ensureLoaded()
    expect(store.hasOrcid).toBe(false)

    getMe.mockResolvedValue({
      data: {
        user: {
          ...ADA,
          identities: [
            ...ADA.identities,
            { id: 'i3', provider: 'orcid', handle: '0000-0002-1825-0097' }
          ]
        }
      }
    })
    await store.ensureLoaded(true)
    expect(store.hasOrcid).toBe(true)
  })

  it('leaves for ORCID with the place to come back to', async () => {
    const assign = vi.fn()
    vi.stubGlobal('location', { ...window.location, assign })
    try {
      const store = useAuthStore()
      await store.goToOrcid({ redirectTo: '/contribute/new' })
      expect(assign).toHaveBeenCalledWith('/api/auth/orcid/start?redirect_to=%2Fcontribute%2Fnew')

      await store.goToOrcid({ redirectTo: '/account', link: true })
      expect(assign).toHaveBeenLastCalledWith(
        '/api/auth/orcid/start?redirect_to=%2Faccount&link=true'
      )
    } finally {
      vi.unstubAllGlobals()
    }
  })

  it('signs in with a code and reports where to land', async () => {
    verifyEmailLogin.mockResolvedValue({
      data: { user: ADA, redirect_to: '/contribute/new' }
    })
    const store = useAuthStore()
    const target = await store.verifyEmailLogin({ code: '123456' })
    expect(target).toBe('/contribute/new')
    expect(store.status).toBe('authenticated')
  })

  it('forgets the user on sign-out, even if the call fails', async () => {
    getMe.mockResolvedValue({ data: { user: ADA } })
    const store = useAuthStore()
    await store.ensureLoaded()
    logout.mockRejectedValue(new Error('network'))

    await expect(store.logout()).rejects.toThrow()
    expect(store.user).toBeNull()
    expect(store.status).toBe('anonymous')
  })

  it('passes the address and the landing page when asking for a code', async () => {
    startEmailLogin.mockResolvedValue({ data: { sent: true } })
    await useAuthStore().startEmailLogin('ada@example.edu', '/curation')
    expect(startEmailLogin).toHaveBeenCalledWith({
      email: 'ada@example.edu',
      redirect_to: '/curation'
    })
  })

  it('reloads the user after unlinking, so the list is right', async () => {
    getMe.mockResolvedValue({ data: { user: ADA } })
    deleteIdentity.mockResolvedValue({ data: undefined })
    const store = useAuthStore()
    await store.ensureLoaded()

    await store.unlinkIdentity('i2')

    expect(deleteIdentity).toHaveBeenCalledWith('i2')
    expect(getMe).toHaveBeenCalledTimes(2)
  })

  it('shows a sent access request as waiting, without asking /auth/me again (#248)', async () => {
    getMe.mockResolvedValue({ data: { user: { ...ADA, role: 'viewer', access_request: null } } })
    const pending = { status: 'pending', role: 'contributor', created_at: '2026-10-05T09:00:00Z' }
    requestAccess.mockResolvedValue({ data: pending })
    const store = useAuthStore()
    await store.ensureLoaded()

    await store.requestAccess('I test braces at ETH.')

    expect(requestAccess).toHaveBeenCalledWith({ message: 'I test braces at ETH.' })
    expect(store.user?.access_request).toEqual(pending)
    expect(getMe).toHaveBeenCalledTimes(1)
  })

  describe('several addresses (#402)', () => {
    const TWO = {
      ...ADA,
      identities: [
        ...ADA.identities,
        { id: 'i3', provider: 'email', handle: 'ada.lovelace@epfl.ch' }
      ]
    }

    it('lists the email identities, and knows the main one', async () => {
      getMe.mockResolvedValue({ data: { user: TWO } })
      const store = useAuthStore()
      await store.ensureLoaded()
      expect(store.emails.map((identity) => identity.handle)).toEqual([
        'ada@example.edu',
        'ada.lovelace@epfl.ch'
      ])
      expect(store.mainEmail).toBe('ada@example.edu')
    })

    it('has no address when nobody is signed in', () => {
      const store = useAuthStore()
      expect(store.emails).toEqual([])
      expect(store.mainEmail).toBeNull()
    })

    it('asks for a code for the new address', async () => {
      startAddEmail.mockResolvedValue({ data: { sent: true } })
      const store = useAuthStore()
      await store.startAddEmail('ada.lovelace@epfl.ch')
      expect(startAddEmail).toHaveBeenCalledWith({ email: 'ada.lovelace@epfl.ch' })
    })

    it('keeps the account the code answers with, without asking /auth/me again', async () => {
      getMe.mockResolvedValue({ data: { user: ADA } })
      verifyAddEmail.mockResolvedValue({ data: TWO })
      const store = useAuthStore()
      await store.ensureLoaded()

      await store.verifyAddEmail('123456')

      expect(verifyAddEmail).toHaveBeenCalledWith({ code: '123456' })
      expect(store.emails).toHaveLength(2)
      expect(getMe).toHaveBeenCalledTimes(1)
    })

    it('says when the address joined this account to another one (#250)', async () => {
      const bare = {
        ...ADA,
        id: 'bare',
        email: null,
        identities: [{ id: 'o1', provider: 'orcid', handle: '0000-0002-1825-0097' }]
      }
      getMe.mockResolvedValue({ data: { user: bare } })
      verifyAddEmail.mockResolvedValue({ data: ADA })
      const store = useAuthStore()
      await store.ensureLoaded()

      expect(await store.verifyAddEmail('123456')).toBe(true)
      expect(store.user?.id).toBe('u1')

      verifyAddEmail.mockResolvedValue({ data: TWO })
      expect(await store.verifyAddEmail('654321')).toBe(false)
    })

    it('lets a wrong code fail, and keeps the account as it was', async () => {
      getMe.mockResolvedValue({ data: { user: ADA } })
      verifyAddEmail.mockRejectedValue(new Error('invalid_or_expired'))
      const store = useAuthStore()
      await store.ensureLoaded()

      await expect(store.verifyAddEmail('000000')).rejects.toThrow()

      expect(store.emails).toHaveLength(1)
    })

    it('reloads the user after a new main address', async () => {
      getMe.mockResolvedValue({ data: { user: TWO } })
      setMainEmail.mockResolvedValue({ data: undefined })
      const store = useAuthStore()
      await store.ensureLoaded()
      getMe.mockResolvedValue({ data: { user: { ...TWO, email: 'ada.lovelace@epfl.ch' } } })

      await store.setMainEmail('i3')

      expect(setMainEmail).toHaveBeenCalledWith('i3')
      expect(store.mainEmail).toBe('ada.lovelace@epfl.ch')
    })
  })
})
