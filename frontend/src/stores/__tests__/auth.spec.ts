import { useAuthStore } from '@/stores/auth'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getMe = vi.fn()
const logout = vi.fn()
const startEmailLogin = vi.fn()
const verifyEmailLogin = vi.fn()
const deleteIdentity = vi.fn()
const requestAccess = vi.fn()

vi.mock('@/plugins/axios', () => ({
  authApi: {
    getMe: (...args: unknown[]) => getMe(...args),
    logout: (...args: unknown[]) => logout(...args),
    startEmailLogin: (...args: unknown[]) => startEmailLogin(...args),
    verifyEmailLogin: (...args: unknown[]) => verifyEmailLogin(...args),
    deleteIdentity: (...args: unknown[]) => deleteIdentity(...args),
    requestAccess: (...args: unknown[]) => requestAccess(...args)
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
})
