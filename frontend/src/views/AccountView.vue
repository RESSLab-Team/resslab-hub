<script setup lang="ts">
/**
 * The account page (#247): who you are here, and what you can sign in with.
 * A viewer can also ask for the contributor role here (#248).
 *
 * An account can hold several email addresses (#402). A new one is added by a
 * code mailed to it and typed here, in the session that asked: never by a
 * link, so nobody can attach their address to someone else's account.
 */
import AccessRequestForm from '@/components/auth/AccessRequestForm.vue'
import { useAuthStore } from '@/stores/auth'
import { mdiCheckCircleOutline, mdiEmailOutline, mdiGithub, mdiLogout, mdiPlus } from '@mdi/js'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t, te } = useI18n({ useScope: 'global' })
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const error = ref('')
const busy = ref(false)

onMounted(async () => {
  await auth.ensureLoaded()
  const reason = route.query.error
  if (reason) error.value = t(`auth.errors.${reason}`, t('auth.errors.generic'))
})

// Why the role is what it is. The backend sends role_source for exactly
// this; an unknown source shows nothing rather than a raw slug.
const roleReason = computed(() => {
  const source = auth.user?.role_source
  return source ? t(`auth.role_source.${source}`, '') : ''
})

const initials = computed(() => {
  const name = auth.user?.display_name || auth.user?.email || '?'
  return name
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
})

const providerIcon = (provider: string) => (provider === 'github' ? mdiGithub : mdiEmailOutline)

/** The email addresses have their own block, so this list is the other ways in. */
const otherIdentities = computed(() =>
  auth.identities.filter((identity) => identity.provider !== 'email')
)

const isMain = (handle: string) => handle.toLowerCase() === auth.mainEmail?.toLowerCase()

function detailOf(caught: unknown): string | undefined {
  return (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
}

/** The add form has its own wording for some slugs, else the shared one. */
function messageFor(detail: string | undefined, scope = 'auth.errors'): string {
  if (detail && te(`${scope}.${detail}`)) return t(`${scope}.${detail}`)
  if (detail && te(`auth.errors.${detail}`)) return t(`auth.errors.${detail}`)
  return t('auth.errors.generic')
}

async function run(action: () => Promise<void>): Promise<void> {
  if (busy.value) return
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    await action()
  } catch (caught: unknown) {
    error.value = messageFor(detailOf(caught))
  } finally {
    busy.value = false
  }
}

const unlink = (id: string) => run(() => auth.unlinkIdentity(id))
const makeMain = (id: string) => run(() => auth.setMainEmail(id))

// --- adding an address: the address first, then the mailed code ---
const addStep = ref<'closed' | 'email' | 'code'>('closed')
const newEmail = ref('')
const addCode = ref('')
const addBusy = ref(false)
const addError = ref('')
const notice = ref('')

const newEmailLooksValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail.value.trim()))
const addCodeLooksValid = computed(() => /^\d{6}$/.test(addCode.value.trim()))

function openAdd(): void {
  addStep.value = 'email'
  newEmail.value = ''
  addCode.value = ''
  addError.value = ''
  notice.value = ''
}

function closeAdd(): void {
  addStep.value = 'closed'
  addError.value = ''
}

async function sendAddCode(): Promise<void> {
  if (!newEmailLooksValid.value || addBusy.value) return
  addBusy.value = true
  addError.value = ''
  try {
    await auth.startAddEmail(newEmail.value.trim())
    addCode.value = ''
    addStep.value = 'code'
  } catch (caught: unknown) {
    addError.value = messageFor(detailOf(caught), 'auth.account.add_errors')
  } finally {
    addBusy.value = false
  }
}

async function confirmAddCode(): Promise<void> {
  if (!addCodeLooksValid.value || addBusy.value) return
  addBusy.value = true
  addError.value = ''
  try {
    await auth.verifyAddEmail(addCode.value.trim())
    notice.value = t('auth.account.email_added', { email: newEmail.value.trim().toLowerCase() })
    addStep.value = 'closed'
  } catch (caught: unknown) {
    addError.value = messageFor(detailOf(caught), 'auth.account.add_errors')
  } finally {
    addBusy.value = false
  }
}

async function signOut(): Promise<void> {
  await auth.logout()
  router.push('/')
}
</script>

<template>
  <div class="account">
    <p class="eyebrow">{{ $t('auth.account.eyebrow') }}</p>
    <h1 class="t-page">{{ $t('auth.account.title') }}</h1>

    <p v-if="error" class="account-error">{{ error }}</p>

    <section v-if="auth.user" class="account-id">
      <div class="avatar">{{ initials }}</div>
      <div class="account-id-text">
        <p class="account-name">{{ auth.user.display_name || $t('auth.account.no_name') }}</p>
        <p class="account-mail">
          {{ auth.user.email || $t('auth.account.no_email') }}
          <span v-if="auth.user.email_verified" class="verified">
            <v-icon :icon="mdiCheckCircleOutline" size="13" />
            {{ $t('auth.account.verified') }}
          </span>
        </p>
        <p v-if="auth.user.institution" class="account-inst">{{ auth.user.institution }}</p>
      </div>
      <div class="role-cell">
        <p class="role-tag">{{ $t(`auth.roles.${auth.user.role}`) }}</p>
        <p v-if="roleReason" class="role-why">{{ roleReason }}</p>
      </div>
    </section>

    <AccessRequestForm class="account-block" />

    <section v-if="auth.user" class="account-block">
      <h2 class="t-panel">{{ $t('auth.account.emails_title') }}</h2>
      <p class="block-lede">{{ $t('auth.account.emails_lede') }}</p>
      <p v-if="notice" class="account-notice">{{ notice }}</p>
      <ul v-if="auth.emails.length" class="identity-list">
        <li v-for="address in auth.emails" :key="address.id">
          <v-icon :icon="mdiEmailOutline" size="18" />
          <span class="identity-handle">{{ address.handle }}</span>
          <span v-if="isMain(address.handle)" class="main-tag">{{ $t('auth.account.main') }}</span>
          <template v-else>
            <button
              class="btn btn-ghost btn-sm"
              type="button"
              :disabled="busy"
              @click="makeMain(address.id)"
            >
              {{ $t('auth.account.make_main') }}
            </button>
            <button
              class="btn btn-ghost btn-sm"
              type="button"
              :disabled="busy"
              @click="unlink(address.id)"
            >
              {{ $t('auth.account.unlink') }}
            </button>
          </template>
        </li>
      </ul>

      <button
        v-if="addStep === 'closed'"
        class="btn btn-secondary btn-sm"
        type="button"
        @click="openAdd"
      >
        <v-icon :icon="mdiPlus" size="16" />
        {{ $t('auth.account.add_email') }}
      </button>

      <div v-else class="add-email">
        <h3 class="add-title">{{ $t('auth.account.add_email') }}</h3>
        <p v-if="addError" class="account-error">{{ addError }}</p>

        <form v-if="addStep === 'email'" @submit.prevent="sendAddCode">
          <p class="block-lede">{{ $t('auth.account.add_email_lede') }}</p>
          <label class="field">
            <span>{{ $t('auth.account.email_label') }}</span>
            <input
              v-model="newEmail"
              type="email"
              autocomplete="email"
              autofocus
              placeholder="name@epfl.ch"
            />
          </label>
          <div class="add-actions">
            <button
              class="btn btn-primary btn-sm"
              type="submit"
              :disabled="!newEmailLooksValid || addBusy"
            >
              {{ $t('auth.account.send_code') }}
            </button>
            <button class="btn btn-ghost btn-sm" type="button" @click="closeAdd">
              {{ $t('auth.account.cancel') }}
            </button>
          </div>
        </form>

        <form v-else @submit.prevent="confirmAddCode">
          <p class="block-lede">
            {{ $t('auth.account.code_sent', { email: newEmail.trim() }) }}
          </p>
          <label class="field">
            <span>{{ $t('auth.account.code_label') }}</span>
            <input
              v-model="addCode"
              class="code-input"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              maxlength="6"
              autofocus
              placeholder="000000"
            />
          </label>
          <div class="add-actions">
            <button
              class="btn btn-primary btn-sm"
              type="submit"
              :disabled="!addCodeLooksValid || addBusy"
            >
              {{ $t('auth.account.confirm') }}
            </button>
            <button class="btn btn-ghost btn-sm" type="button" @click="openAdd">
              {{ $t('auth.login.other_email') }}
            </button>
          </div>
        </form>
      </div>
    </section>

    <section class="account-block">
      <h2 class="t-panel">{{ $t('auth.account.identities') }}</h2>
      <p class="block-lede">{{ $t('auth.account.identities_lede') }}</p>
      <ul v-if="otherIdentities.length" class="identity-list">
        <li v-for="identity in otherIdentities" :key="identity.id">
          <v-icon :icon="providerIcon(identity.provider)" size="18" />
          <span class="identity-provider">{{ $t(`auth.providers.${identity.provider}`) }}</span>
          <span class="identity-handle">{{ identity.handle }}</span>
          <button
            v-if="auth.identities.length > 1"
            class="btn btn-ghost btn-sm"
            type="button"
            :disabled="busy"
            @click="unlink(identity.id)"
          >
            {{ $t('auth.account.unlink') }}
          </button>
        </li>
      </ul>
      <button
        v-if="!auth.hasGitHub"
        class="btn btn-secondary btn-sm"
        type="button"
        @click="auth.goToGitHub({ redirectTo: '/account', link: true })"
      >
        <v-icon :icon="mdiGithub" size="16" />
        {{ $t('auth.account.link_github') }}
      </button>
      <p v-if="!auth.hasGitHub" class="block-lede">{{ $t('auth.account.link_github_why') }}</p>
      <p v-if="!auth.hasGitHub" class="block-lede">{{ $t('auth.account.github_role_hint') }}</p>
    </section>

    <section class="account-block">
      <button class="btn btn-secondary btn-sm" type="button" @click="signOut">
        <v-icon :icon="mdiLogout" size="16" />
        {{ $t('auth.account.sign_out') }}
      </button>
    </section>
  </div>
</template>

<style scoped>
.account {
  max-width: 680px;
  padding: clamp(24px, 5vw, 48px) clamp(16px, 4vw, 32px) 96px;
}
.account-error {
  margin: 20px 0 0;
  padding: 10px 12px;
  border-left: 3px solid var(--epfl-red);
  background: var(--bg-subtle);
  font-size: 13px;
}
.account-id {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 16px;
  margin: 28px 0 0;
  padding: 20px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
.avatar {
  flex: none;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  background: var(--epfl-red);
  color: #fff;
  font-weight: 700;
  font-size: 15px;
}
.account-id-text {
  flex: 1;
  min-width: 0;
}
.account-name {
  margin: 0;
  font-weight: 600;
  font-size: 15px;
}
.account-mail {
  margin: 4px 0 0;
  color: var(--fg-muted);
  font-size: 13px;
  /* A long address breaks instead of pushing the page wider. */
  overflow-wrap: anywhere;
}
.verified {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: 8px;
  color: var(--epfl-leman, #00a79f);
}
.account-inst {
  margin: 2px 0 0;
  color: var(--fg-muted);
  font-size: 13px;
}
.role-cell {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.role-why {
  margin: 0;
  max-width: 220px;
  font-size: 11px;
  line-height: 15px;
  text-align: right;
  color: var(--fg-muted);
}

/* Phone: the role goes on its own line under the name, read left to right,
   instead of squeezing the name into a thin column. */
@media (max-width: 600px) {
  .role-cell {
    flex: 1 1 100%;
    align-items: flex-start;
  }
  .role-why {
    max-width: none;
    text-align: left;
  }
}

.role-tag {
  flex: none;
  margin: 0;
  padding: 3px 8px;
  border: 1px solid var(--border-strong);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.account-block {
  margin-top: 36px;
}
.block-lede {
  margin: 8px 0 16px;
  color: var(--fg-muted);
  font-size: 13px;
  line-height: 1.5;
  max-width: 60ch;
}
.identity-list {
  margin: 0 0 16px;
  padding: 0;
  list-style: none;
}
.identity-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.identity-provider {
  font-weight: 600;
}
.identity-handle {
  flex: 1;
  min-width: 0;
  color: var(--fg-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.main-tag {
  flex: none;
  padding: 2px 6px;
  border: 1px solid var(--border-strong);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.account-notice {
  margin: 0 0 16px;
  padding: 10px 12px;
  border-left: 3px solid var(--epfl-leman, #00a79f);
  background: var(--bg-subtle);
  font-size: 13px;
}
.add-email {
  max-width: 420px;
  padding-top: 4px;
}
.add-email .account-error {
  margin: 0 0 16px;
}
.add-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}
.add-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.field {
  display: block;
  margin-bottom: 16px;
}
.field span {
  display: block;
  margin-bottom: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fg-muted);
}
.field input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
}
.field input:focus {
  outline: none;
  border-color: var(--epfl-red);
}
.code-input {
  font-family: var(--font-mono, monospace);
  font-size: 20px;
  letter-spacing: 0.4em;
}
</style>
