<script setup lang="ts">
/**
 * The account page (#247): who you are here, and what you can sign in with.
 * A viewer can also ask for the contributor role here (#248).
 */
import AccessRequestForm from '@/components/auth/AccessRequestForm.vue'
import { useAuthStore } from '@/stores/auth'
import { mdiCheckCircleOutline, mdiEmailOutline, mdiGithub, mdiLogout } from '@mdi/js'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })
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

async function unlink(id: string): Promise<void> {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await auth.unlinkIdentity(id)
  } catch (caught: unknown) {
    const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error.value = t(`auth.errors.${detail}`, t('auth.errors.generic'))
  } finally {
    busy.value = false
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

    <section class="account-block">
      <h2 class="t-panel">{{ $t('auth.account.identities') }}</h2>
      <p class="block-lede">{{ $t('auth.account.identities_lede') }}</p>
      <ul class="identity-list">
        <li v-for="identity in auth.identities" :key="identity.id">
          <v-icon :icon="providerIcon(identity.provider)" size="18" />
          <span class="identity-provider">{{ $t(`auth.providers.${identity.provider}`) }}</span>
          <span class="identity-handle">{{ identity.handle }}</span>
          <button
            v-if="identity.provider !== 'email' && auth.identities.length > 1"
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
</style>
