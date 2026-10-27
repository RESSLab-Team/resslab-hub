/**
 * The admin page (#248): members, invitations and access requests.
 *
 * Not cached across visits like the curation store: an admin opens this page
 * to change something, and must see what the others changed meanwhile. Every
 * action writes the row the backend sends back, so a click does not reload
 * the page (an approval reads the members again, its role may have changed).
 */

import type {
  AccessRequestOut,
  AdminUserOut,
  AdminUserPatch,
  InvitationIn,
  InvitationOut
} from '@/backend'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

// Lazy and shared, like the other stores (see stores/curation.ts).
let apiModule: Promise<typeof import('@/plugins/axios')> | null = null
function api(): Promise<typeof import('@/plugins/axios')> {
  apiModule ??= import('@/plugins/axios')
  return apiModule
}

/** The slug the backend sent in `detail`, for an i18n key. */
export function errorCode(caught: unknown): string {
  const detail = (caught as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'generic'
}

function replace<T extends { id: string }>(list: T[], item: T): T[] {
  return list.map((entry) => (entry.id === item.id ? item : entry))
}

export const useAdminStore = defineStore('admin', () => {
  const users = ref<AdminUserOut[]>([])
  const invitations = ref<InvitationOut[]>([])
  const requests = ref<AccessRequestOut[]>([])
  const state = ref<'idle' | 'loading' | 'ready' | 'error'>('idle')

  const pendingRequests = computed(() => requests.value.filter((item) => item.status === 'pending'))
  const pendingInvitations = computed(() =>
    invitations.value.filter((item) => item.status === 'pending')
  )

  async function fetchAll(): Promise<void> {
    state.value = 'loading'
    try {
      const { adminApi } = await api()
      const [usersResponse, invitationsResponse, requestsResponse] = await Promise.all([
        adminApi.listUsers(),
        adminApi.listInvitations(),
        adminApi.listAccessRequests()
      ])
      users.value = usersResponse.data
      invitations.value = invitationsResponse.data
      requests.value = requestsResponse.data
      state.value = 'ready'
    } catch {
      state.value = 'error'
    }
  }

  async function updateUser(id: string, patch: AdminUserPatch): Promise<void> {
    const { adminApi } = await api()
    const { data } = await adminApi.updateUser(id, patch)
    users.value = replace(users.value, data)
  }

  /** Invite an address. Resolves with whether the mail went out. */
  async function invite(payload: InvitationIn): Promise<boolean> {
    const { adminApi } = await api()
    const { data } = await adminApi.createInvitation(payload)
    const { mailed, ...invitation } = data
    invitations.value = [invitation, ...invitations.value]
    return mailed ?? false
  }

  async function revokeInvitation(id: string): Promise<void> {
    const { adminApi } = await api()
    await adminApi.revokeInvitation(id)
    invitations.value = invitations.value.map((item) =>
      item.id === id ? { ...item, status: 'revoked', revoked_at: new Date().toISOString() } : item
    )
  }

  async function decide(id: string, approve: boolean): Promise<void> {
    const { adminApi } = await api()
    const { data } = approve
      ? await adminApi.approveAccessRequest(id)
      : await adminApi.declineAccessRequest(id)
    requests.value = replace(requests.value, data)
    // An approval may change a member's role: read the members again rather
    // than guess what the backend decided.
    if (approve) users.value = (await adminApi.listUsers()).data
  }

  return {
    users,
    invitations,
    requests,
    state,
    pendingRequests,
    pendingInvitations,
    fetchAll,
    updateUser,
    invite,
    revokeInvitation,
    decide
  }
})
