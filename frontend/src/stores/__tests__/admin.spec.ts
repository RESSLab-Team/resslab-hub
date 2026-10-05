import { errorCode, useAdminStore } from '@/stores/admin'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const listUsers = vi.fn()
const listInvitations = vi.fn()
const listAccessRequests = vi.fn()
const updateUser = vi.fn()
const createInvitation = vi.fn()
const revokeInvitation = vi.fn()
const approveAccessRequest = vi.fn()
const declineAccessRequest = vi.fn()

vi.mock('@/plugins/axios', () => ({
  adminApi: {
    listUsers: (...args: unknown[]) => listUsers(...args),
    listInvitations: (...args: unknown[]) => listInvitations(...args),
    listAccessRequests: (...args: unknown[]) => listAccessRequests(...args),
    updateUser: (...args: unknown[]) => updateUser(...args),
    createInvitation: (...args: unknown[]) => createInvitation(...args),
    revokeInvitation: (...args: unknown[]) => revokeInvitation(...args),
    approveAccessRequest: (...args: unknown[]) => approveAccessRequest(...args),
    declineAccessRequest: (...args: unknown[]) => declineAccessRequest(...args)
  }
}))

const ADA = {
  id: 'u1',
  email: 'ada@example.org',
  role: 'viewer',
  role_source: 'default',
  created_at: '2026-09-01T10:00:00Z'
}
const REQUEST = {
  id: 'r1',
  user_id: 'u1',
  current_role: 'viewer',
  role: 'contributor',
  status: 'pending',
  created_at: '2026-10-01T10:00:00Z'
}
const INVITATION = {
  id: 'i1',
  email: 'bob@example.org',
  role: 'curator',
  status: 'pending',
  created_at: '2026-10-02T10:00:00Z'
}

async function loaded() {
  listUsers.mockResolvedValue({ data: [ADA] })
  listInvitations.mockResolvedValue({ data: [INVITATION] })
  listAccessRequests.mockResolvedValue({ data: [REQUEST] })
  const store = useAdminStore()
  await store.fetchAll()
  return store
}

describe('admin store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads the three lists together', async () => {
    const store = await loaded()
    expect(store.state).toBe('ready')
    expect(store.users).toHaveLength(1)
    expect(store.pendingRequests).toHaveLength(1)
    expect(store.pendingInvitations).toHaveLength(1)
  })

  it('shows an error when one list fails', async () => {
    listUsers.mockRejectedValue(new Error('network'))
    listInvitations.mockResolvedValue({ data: [] })
    listAccessRequests.mockResolvedValue({ data: [] })
    const store = useAdminStore()
    await store.fetchAll()
    expect(store.state).toBe('error')
  })

  it('writes the member the backend sends back', async () => {
    const store = await loaded()
    updateUser.mockResolvedValue({
      data: { ...ADA, role: 'curator', role_source: 'override', role_override: 'curator' }
    })
    await store.updateUser('u1', { role_override: 'curator' })
    expect(updateUser).toHaveBeenCalledWith('u1', { role_override: 'curator' })
    expect(store.users[0]?.role).toBe('curator')
  })

  it('puts a new invitation first, and says whether it was mailed', async () => {
    const store = await loaded()
    createInvitation.mockResolvedValue({
      data: { ...INVITATION, id: 'i2', email: 'cleo@example.org', mailed: false }
    })
    const mailed = await store.invite({ email: 'cleo@example.org', role: 'curator' })
    expect(mailed).toBe(false)
    expect(store.invitations.map((item) => item.id)).toEqual(['i2', 'i1'])
    expect(store.invitations[0]).not.toHaveProperty('mailed')
  })

  it('marks a revoked invitation without reloading', async () => {
    const store = await loaded()
    revokeInvitation.mockResolvedValue({})
    await store.revokeInvitation('i1')
    expect(store.pendingInvitations).toHaveLength(0)
    expect(listInvitations).toHaveBeenCalledTimes(1)
  })

  it('reads the members again after an approval, not after a decline', async () => {
    const store = await loaded()
    approveAccessRequest.mockResolvedValue({
      data: { ...REQUEST, status: 'approved', current_role: 'contributor' }
    })
    listUsers.mockResolvedValue({ data: [{ ...ADA, role: 'contributor' }] })
    await store.decide('r1', true)
    expect(store.pendingRequests).toHaveLength(0)
    expect(store.users[0]?.role).toBe('contributor')
    expect(listUsers).toHaveBeenCalledTimes(2)

    declineAccessRequest.mockResolvedValue({ data: { ...REQUEST, status: 'declined' } })
    await store.decide('r1', false)
    expect(listUsers).toHaveBeenCalledTimes(2)
  })

  it('reads the slug out of an error, or falls back to generic', () => {
    expect(errorCode({ response: { data: { detail: 'locked_admin' } } })).toBe('locked_admin')
    expect(errorCode({ response: { data: { detail: [{ msg: 'bad' }] } } })).toBe('generic')
    expect(errorCode(new Error('network'))).toBe('generic')
  })
})
