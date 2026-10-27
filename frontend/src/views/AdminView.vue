<script setup lang="ts">
/**
 * Who can do what (#248): access requests, members, invitations.
 *
 * Admins only (the route and the backend both check). An admin cannot change
 * their own row, nor an admin who comes from GitHub or from ADMIN_EMAILS: the
 * backend refuses it, so the page shows those rows read-only.
 */
import ProgressLine from '@/components/commons/ProgressLine.vue'
import type { AccessRequestOut, AdminUserOut, InvitationInRoleEnum } from '@/backend'
import { errorCode, useAdminStore } from '@/stores/admin'
import { useAuthStore } from '@/stores/auth'
import { formatAge } from '@/utils/curation'
import { mdiAlertOutline, mdiRefresh } from '@mdi/js'
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n({ useScope: 'global' })
const store = useAdminStore()
const auth = useAuthStore()

onMounted(() => store.fetchAll())

const ROLES = ['viewer', 'contributor', 'curator', 'admin'] as const
const INVITE_ROLES: InvitationInRoleEnum[] = ['contributor', 'curator', 'admin']

// One message per section, shown next to what failed.
const errors = reactive({ requests: '', members: '', invitations: '' })
const busy = ref('')

async function run(section: keyof typeof errors, key: string, action: () => Promise<unknown>) {
  if (busy.value) return
  busy.value = key
  errors[section] = ''
  try {
    await action()
  } catch (caught: unknown) {
    errors[section] = t(`admin.errors.${errorCode(caught)}`, t('admin.errors.generic'))
  } finally {
    busy.value = ''
  }
}

function initialsOf(name: string): string {
  const parts = name
    .trim()
    .split(/[\s@.]+/)
    .filter(Boolean)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?'
}

// --- access requests ---------------------------------------------------------
const decidedRequests = computed(() => store.requests.filter((item) => item.status !== 'pending'))

function decide(item: AccessRequestOut, approve: boolean): Promise<void> {
  return run('requests', item.id, () => store.decide(item.id, approve))
}

// --- members -----------------------------------------------------------------
const isSelf = (user: AdminUserOut) => user.id === auth.user?.id

/** Why a row cannot be changed here, or '' when it can. */
function readOnlyReason(user: AdminUserOut): string {
  if (isSelf(user)) return t('admin.members.you')
  if (!user.locked) return ''
  return user.role_source === 'github'
    ? t('admin.members.locked_github')
    : t('admin.members.locked_config')
}

function setRole(user: AdminUserOut, event: Event): Promise<void> {
  const value = (event.target as HTMLSelectElement).value
  const role = value ? (value as (typeof ROLES)[number]) : null
  return run('members', user.id, () => store.updateUser(user.id, { role_override: role }))
}

// Disabling signs the person out everywhere: the button asks twice.
const confirming = ref('')

function toggleAccess(user: AdminUserOut): Promise<void> | void {
  if (!user.disabled && confirming.value !== user.id) {
    confirming.value = user.id
    return
  }
  confirming.value = ''
  return run('members', user.id, () => store.updateUser(user.id, { disabled: !user.disabled }))
}

// --- invitations -------------------------------------------------------------
const inviteEmail = ref('')
const inviteRole = ref<InvitationInRoleEnum>('contributor')
const inviteNotice = ref<{ text: string; warn: boolean } | null>(null)

async function invite(): Promise<void> {
  const email = inviteEmail.value.trim()
  if (!email) return
  inviteNotice.value = null
  await run('invitations', 'invite', async () => {
    const mailed = await store.invite({ email, role: inviteRole.value })
    inviteNotice.value = mailed
      ? { text: t('admin.invitations.sent', { email }), warn: false }
      : { text: t('admin.invitations.not_mailed', { email }), warn: true }
    inviteEmail.value = ''
  })
}
</script>

<template>
  <div class="admin-page">
    <div class="phead">
      <p class="eyebrow">
        <span class="red">{{ $t('admin.eyebrow') }}</span>
        <span class="mut"> · {{ $t('admin.eyebrow_qualifier') }}</span>
      </p>
      <div class="prow">
        <h1 class="ptitle">
          {{ $t('admin.title') }}
          <span v-if="store.state === 'ready'" class="cnt">{{ store.users.length }}</span>
        </h1>
        <button
          v-if="store.state === 'ready'"
          class="cp-btn"
          type="button"
          @click="store.fetchAll()"
        >
          <v-icon :icon="mdiRefresh" size="14" />
          {{ $t('curation.queue.refresh') }}
        </button>
      </div>
      <p class="pdesc">{{ $t('admin.description') }}</p>
    </div>

    <div class="pbody">
      <progress-line
        v-if="store.state === 'loading' || store.state === 'idle'"
        :active="true"
        :label="$t('admin.loading')"
      />
      <p v-else-if="store.state === 'error'" class="state">
        <v-icon :icon="mdiAlertOutline" size="15" />
        {{ $t('admin.error') }}
        <button class="cp-btn" type="button" @click="store.fetchAll()">
          {{ $t('admin.retry') }}
        </button>
      </p>

      <template v-else>
        <!-- Access requests -->
        <section class="block">
          <h2 class="t-panel">
            {{ $t('admin.requests.title') }}
            <span class="cnt">{{ store.pendingRequests.length }}</span>
          </h2>
          <p v-if="errors.requests" class="notice warn">{{ errors.requests }}</p>
          <p v-if="store.pendingRequests.length === 0" class="state">
            {{ $t('admin.requests.empty') }}
          </p>
          <ul v-else class="requests">
            <li v-for="item in store.pendingRequests" :key="item.id" class="request">
              <div class="userline">
                <span class="ava">{{ initialsOf(item.display_name || item.email || '') }}</span>
                <span class="who">
                  <span class="un">{{ item.display_name || item.email }}</span>
                  <span class="ue">
                    {{ item.email
                    }}<template v-if="item.institution"> · {{ item.institution }}</template>
                  </span>
                </span>
              </div>
              <p class="asks">
                {{ $t('admin.requests.asks_for', { role: $t(`auth.roles.${item.role}`) }) }}
                <span class="mono mut">· {{ formatAge(item.created_at, locale) }}</span>
              </p>
              <p v-if="item.message" class="message">{{ item.message }}</p>
              <div class="request-actions">
                <button
                  class="btn btn-secondary btn-sm"
                  type="button"
                  :disabled="!!busy"
                  @click="decide(item, true)"
                >
                  {{ $t('admin.requests.approve') }}
                </button>
                <button
                  class="btn btn-ghost btn-sm"
                  type="button"
                  :disabled="!!busy"
                  @click="decide(item, false)"
                >
                  {{ $t('admin.requests.decline') }}
                </button>
              </div>
            </li>
          </ul>
          <details v-if="decidedRequests.length" class="decided">
            <summary>{{ $t('admin.requests.decided', { count: decidedRequests.length }) }}</summary>
            <ul>
              <li v-for="item in decidedRequests" :key="item.id">
                <span class="un">{{ item.display_name || item.email }}</span>
                <span class="mut">
                  {{
                    $t('admin.requests.decided_by', {
                      status: $t(`admin.requests.status.${item.status}`),
                      name: item.decided_by || '?',
                      age: item.decided_at ? formatAge(item.decided_at, locale) : ''
                    })
                  }}
                </span>
              </li>
            </ul>
          </details>
        </section>

        <!-- Members -->
        <section class="block">
          <h2 class="t-panel">{{ $t('admin.members.title') }}</h2>
          <p v-if="errors.members" class="notice warn">{{ errors.members }}</p>
          <p v-if="store.users.length === 0" class="state">{{ $t('admin.members.empty') }}</p>
          <div v-else class="tablewrap">
            <table class="grid">
              <thead>
                <tr>
                  <th>{{ $t('admin.members.headers.member') }}</th>
                  <th>{{ $t('admin.members.headers.role') }}</th>
                  <th>{{ $t('admin.members.headers.decision') }}</th>
                  <th>{{ $t('admin.members.headers.github') }}</th>
                  <th>{{ $t('admin.members.headers.last_login') }}</th>
                  <th>{{ $t('admin.members.headers.access') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in store.users" :key="user.id" :class="{ off: user.disabled }">
                  <td>
                    <div class="userline">
                      <span class="ava">{{
                        initialsOf(user.display_name || user.email || '')
                      }}</span>
                      <span class="who">
                        <span class="un">{{ user.display_name || user.email }}</span>
                        <span class="ue">
                          {{ user.email || '—' }}
                          <template v-if="user.email && !user.email_verified">
                            ({{ $t('admin.members.unverified') }})</template
                          >
                        </span>
                        <span v-if="user.institution" class="ue">{{ user.institution }}</span>
                      </span>
                    </div>
                  </td>
                  <td>
                    <span class="tag">{{ $t(`auth.roles.${user.role}`) }}</span>
                    <span class="src">{{
                      $t(`admin.members.source.${user.role_source}`, user.role_source)
                    }}</span>
                  </td>
                  <td>
                    <span v-if="readOnlyReason(user)" class="mut">{{ readOnlyReason(user) }}</span>
                    <select
                      v-else
                      class="field"
                      :value="user.role_override ?? ''"
                      :disabled="!!busy"
                      :aria-label="$t('admin.members.headers.decision')"
                      @change="setRole(user, $event)"
                    >
                      <option value="">{{ $t('admin.members.automatic') }}</option>
                      <option v-for="role in ROLES" :key="role" :value="role">
                        {{ $t(`auth.roles.${role}`) }}
                      </option>
                    </select>
                  </td>
                  <td class="mono">
                    <template v-if="user.github_login">
                      {{ user.github_login }}
                      <span v-if="user.github_role" class="mut">· {{ user.github_role }}</span>
                    </template>
                    <span v-else class="mut">—</span>
                  </td>
                  <td class="mono mut">
                    {{
                      user.last_login_at
                        ? formatAge(user.last_login_at, locale)
                        : $t('admin.members.never')
                    }}
                  </td>
                  <td class="actions">
                    <span v-if="user.disabled" class="tag off-tag">{{
                      $t('admin.members.disabled')
                    }}</span>
                    <button
                      v-if="!readOnlyReason(user)"
                      class="btn btn-ghost btn-sm"
                      type="button"
                      :disabled="!!busy"
                      @click="toggleAccess(user)"
                      @blur="confirming === user.id && (confirming = '')"
                    >
                      {{
                        user.disabled
                          ? $t('admin.members.enable')
                          : confirming === user.id
                          ? $t('admin.members.confirm_disable')
                          : $t('admin.members.disable')
                      }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- Invitations -->
        <section class="block">
          <h2 class="t-panel">
            {{ $t('admin.invitations.title') }}
            <span class="cnt">{{ store.pendingInvitations.length }}</span>
          </h2>
          <p class="lede">{{ $t('admin.invitations.lede') }}</p>
          <form class="invite" @submit.prevent="invite">
            <label class="lbl">
              {{ $t('admin.invitations.email') }}
              <input
                v-model="inviteEmail"
                class="field"
                type="email"
                required
                autocomplete="off"
                placeholder="name@example.org"
              />
            </label>
            <label class="lbl">
              {{ $t('admin.invitations.role') }}
              <select v-model="inviteRole" class="field">
                <option v-for="role in INVITE_ROLES" :key="role" :value="role">
                  {{ $t(`auth.roles.${role}`) }}
                </option>
              </select>
            </label>
            <button class="btn btn-primary btn-sm" type="submit" :disabled="!!busy">
              {{ $t('admin.invitations.send') }}
            </button>
          </form>
          <p v-if="errors.invitations" class="notice warn">{{ errors.invitations }}</p>
          <p v-else-if="inviteNotice" class="notice" :class="{ warn: inviteNotice.warn }">
            {{ inviteNotice.text }}
          </p>
          <p v-if="store.invitations.length === 0" class="state">
            {{ $t('admin.invitations.empty') }}
          </p>
          <ul v-else class="invitations">
            <li v-for="item in store.invitations" :key="item.id">
              <span class="mono inv-email">{{ item.email }}</span>
              <span class="tag">{{ $t(`auth.roles.${item.role}`) }}</span>
              <span class="mut inv-meta">
                {{ $t(`admin.invitations.status.${item.status}`) }} ·
                {{
                  $t('admin.invitations.invited_by', {
                    name: item.invited_by || '?',
                    age: formatAge(item.created_at, locale)
                  })
                }}
              </span>
              <button
                v-if="item.status === 'pending'"
                class="btn btn-ghost btn-sm"
                type="button"
                :disabled="!!busy"
                @click="run('invitations', item.id, () => store.revokeInvitation(item.id))"
              >
                {{ $t('admin.invitations.revoke') }}
              </button>
            </li>
          </ul>
        </section>
      </template>
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  min-height: 100%;
  background: var(--bg);
}

/* ── page head, the same as the review queue ── */
.phead {
  padding: 30px clamp(20px, 3vw, 56px) 22px;
  border-bottom: 1px solid var(--fg);
}
.eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin: 0 0 14px;
}
.eyebrow .red {
  color: var(--primary);
}
.eyebrow .mut {
  color: var(--fg-subtle);
}
.prow {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px 24px;
}
.ptitle {
  font-size: 40px;
  font-weight: 300;
  letter-spacing: -0.02em;
  line-height: 1;
  margin: 0;
}
.cnt {
  font-size: 15px;
  font-weight: 400;
  color: var(--fg-muted);
  margin-left: 14px;
  font-family: var(--font-mono);
  font-feature-settings: 'tnum';
}
.t-panel .cnt {
  font-size: 12px;
  margin-left: 8px;
}
.pdesc {
  font-size: 14px;
  color: var(--fg-muted);
  line-height: 1.5;
  max-width: 74ch;
  margin: 16px 0 0;
}
.cp-btn {
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  padding: 10px 16px;
  border: 1px solid var(--fg);
  background: var(--bg);
  color: var(--fg);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  white-space: nowrap;
}
.cp-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.pbody {
  padding: 26px clamp(20px, 3vw, 56px) 50px;
}
.block + .block {
  margin-top: 44px;
}
.block .t-panel {
  margin: 0 0 14px;
}
.state {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 14px;
  color: var(--fg-muted);
}
.lede {
  margin: 0 0 16px;
  max-width: 74ch;
  font-size: 13px;
  line-height: 1.5;
  color: var(--fg-muted);
}
.notice {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-left: 3px solid var(--border-strong);
  background: var(--bg-subtle);
  font-size: 13px;
  line-height: 1.5;
  max-width: 74ch;
}
.notice.warn {
  border-left-color: var(--primary);
}
.mono {
  font-family: var(--font-mono);
  font-size: 12px;
  font-feature-settings: 'tnum';
}
.mut {
  color: var(--fg-muted);
}
.tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 2px 7px;
  border: 1px solid var(--border);
  white-space: nowrap;
}

/* ── people ── */
.userline {
  display: flex;
  align-items: center;
  gap: 11px;
}
.ava {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--fg);
  color: var(--bg);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}
.who {
  min-width: 0;
}
.un {
  display: block;
  font-weight: 600;
}
.ue {
  display: block;
  font-size: 12px;
  color: var(--fg-subtle);
  margin-top: 1px;
  overflow-wrap: anywhere;
}

/* ── access requests ── */
.requests {
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--border);
}
.request {
  padding: 16px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.asks {
  margin: 10px 0 0 41px;
}
.message {
  margin: 8px 0 0 41px;
  padding: 2px 0 2px 12px;
  border-left: 1px solid var(--border-strong);
  max-width: 74ch;
  white-space: pre-wrap;
  line-height: 1.5;
}
.request-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0 0 41px;
}
.decided {
  margin-top: 14px;
  font-size: 13px;
}
.decided summary {
  cursor: pointer;
  color: var(--fg-muted);
}
.decided ul {
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
}
.decided li {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.decided .un {
  display: inline;
}

/* ── members table, the same as the review queue ── */
.tablewrap {
  border: 1px solid var(--border);
  overflow-x: auto;
}
.grid {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.grid thead th {
  text-align: left;
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
  font-weight: 700;
  padding: 12px 16px;
  border-bottom: 1px solid var(--fg);
  background: var(--bg-subtle);
  white-space: nowrap;
}
.grid tbody td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: middle;
}
.grid tbody tr:last-child td {
  border-bottom: 0;
}
.grid tr.off td {
  color: var(--fg-muted);
}
.src {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: var(--fg-subtle);
}
.actions {
  white-space: nowrap;
  text-align: right;
}
.off-tag {
  margin-right: 8px;
}

/* ── form fields ── */
.field {
  min-width: 0;
  padding: 7px 10px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  font-size: 13px;
}
.field:focus {
  outline: 2px solid var(--fg);
  outline-offset: -1px;
}
select.field {
  padding-right: 6px;
}

/* ── invitations ── */
.invite {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
  margin: 0 0 16px;
}
.lbl {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
}
.invite input.field {
  width: min(340px, 100%);
}
.invitations {
  margin: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--border);
}
.invitations li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.inv-email {
  font-size: 13px;
  overflow-wrap: anywhere;
}
.inv-meta {
  flex: 1;
  min-width: 12em;
}

@media (max-width: 600px) {
  .ptitle {
    font-size: 30px;
  }
  .asks,
  .message,
  .request-actions {
    margin-left: 0;
  }
  .invite .lbl,
  .invite input.field {
    width: 100%;
  }
}
</style>
