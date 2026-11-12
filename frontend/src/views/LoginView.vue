<script setup lang="ts">
/**
 * Sign in (#247).
 *
 * Two steps in one page: ask for an address, then type the code that arrives.
 * The mail also carries a link, which lands on LoginVerifyView instead, so
 * whichever device holds the mailbox works.
 *
 * ORCID (#250) needs nothing from EPFL IT: a public API client is free.
 * The other academic providers of the mockup (EPFL, eduGAIN) come with #249
 * and #252, each with a registration EPFL IT has to file.
 */
import OrcidIcon from '@/components/auth/OrcidIcon.vue'
import { useAuthStore } from '@/stores/auth'
import { mdiAlertCircleOutline, mdiArrowLeft, mdiEmailOutline, mdiGithub } from '@mdi/js'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const step = ref<'email' | 'code'>('email')
const email = ref('')
const code = ref('')
const busy = ref(false)
const error = ref('')

/** Where to land afterwards; the guard puts it there when it redirects here. */
const next = computed(() => {
  const value = route.query.next
  const target = Array.isArray(value) ? value[0] : value
  return target && target.startsWith('/') && !target.startsWith('//') ? target : '/'
})

const emailLooksValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()))
const codeLooksValid = computed(() => /^\d{6}$/.test(code.value.trim()))

onMounted(() => {
  // The GitHub and ORCID round trips come back here with a reason when it could not
  // finish, since a redirect has no other way to report one.
  const reason = route.query.error
  if (reason) error.value = t(`auth.errors.${reason}`, t('auth.errors.generic'))
})

async function sendCode(): Promise<void> {
  if (!emailLooksValid.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await auth.startEmailLogin(email.value.trim(), next.value)
    step.value = 'code'
  } catch (caught: unknown) {
    // The backend says "mail_failed" when the relay is down. Anything else
    // falls back to the generic line.
    const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error.value = t(`auth.errors.${detail}`, t('auth.errors.generic'))
  } finally {
    busy.value = false
  }
}

async function submitCode(): Promise<void> {
  if (!codeLooksValid.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    const target = await auth.verifyEmailLogin({ code: code.value.trim() })
    router.replace(target)
  } catch (caught: unknown) {
    const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error.value = t(`auth.errors.${detail}`, t('auth.errors.generic'))
  } finally {
    busy.value = false
  }
}

function restart(): void {
  step.value = 'email'
  code.value = ''
  error.value = ''
}
</script>

<template>
  <div class="login">
    <div class="login-card">
      <p class="eyebrow">{{ $t('auth.login.eyebrow') }}</p>
      <h1 class="t-page">{{ $t('auth.login.title') }}</h1>
      <p class="login-lede">{{ $t('auth.login.lede') }}</p>

      <p v-if="error" class="login-error">
        <v-icon :icon="mdiAlertCircleOutline" size="16" />
        <span>{{ error }}</span>
      </p>

      <template v-if="step === 'email'">
        <button class="provider" type="button" @click="auth.goToGitHub({ redirectTo: next })">
          <v-icon :icon="mdiGithub" size="20" />
          <span>{{ $t('auth.login.github') }}</span>
        </button>
        <p class="provider-note">{{ $t('auth.login.github_note') }}</p>

        <button
          class="provider provider-next"
          type="button"
          @click="auth.goToOrcid({ redirectTo: next })"
        >
          <OrcidIcon :size="20" />
          <span>{{ $t('auth.login.orcid') }}</span>
        </button>
        <p class="provider-note">{{ $t('auth.login.orcid_note') }}</p>

        <div class="sep">
          <span>{{ $t('auth.login.or_email') }}</span>
        </div>

        <form @submit.prevent="sendCode">
          <label class="field">
            <span>{{ $t('auth.login.email_label') }} *</span>
            <input
              v-model="email"
              type="email"
              autocomplete="email"
              autofocus
              placeholder="you@university.edu"
            />
          </label>
          <button
            class="btn btn-primary login-submit"
            type="submit"
            :disabled="!emailLooksValid || busy"
          >
            <v-icon :icon="mdiEmailOutline" size="16" />
            {{ busy ? $t('auth.login.sending') : $t('auth.login.send_code') }}
          </button>
        </form>
      </template>

      <template v-else>
        <p class="login-sent">{{ $t('auth.login.sent', { email: email.trim() }) }}</p>
        <form @submit.prevent="submitCode">
          <label class="field">
            <span>{{ $t('auth.login.code_label') }}</span>
            <input
              v-model="code"
              class="code-input"
              type="text"
              inputmode="numeric"
              autocomplete="one-time-code"
              maxlength="6"
              autofocus
              placeholder="000000"
            />
          </label>
          <button
            class="btn btn-primary login-submit"
            type="submit"
            :disabled="!codeLooksValid || busy"
          >
            {{ busy ? $t('auth.login.checking') : $t('auth.login.confirm') }}
          </button>
        </form>
        <button class="btn btn-ghost btn-sm login-back" type="button" @click="restart">
          <v-icon :icon="mdiArrowLeft" size="14" />
          {{ $t('auth.login.other_email') }}
        </button>
      </template>

      <p class="login-foot">{{ $t('auth.login.browsing_is_free') }}</p>
    </div>
  </div>
</template>

<style scoped>
.login {
  display: flex;
  justify-content: center;
  padding: 64px 24px 96px;
}
.login-card {
  width: 100%;
  max-width: 460px;
}
.login-lede {
  margin: 12px 0 28px;
  color: var(--fg-muted);
  font-size: 14px;
  line-height: 1.5;
}
.login-error {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0 0 20px;
  padding: 10px 12px;
  border-left: 3px solid var(--epfl-red);
  background: var(--bg-subtle);
  color: var(--fg);
  font-size: 13px;
  line-height: 1.45;
}
/* Full-width, like the mockup: the providers stack (GitHub, ORCID, then
   #249 and #252). */
.provider {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 16px 18px;
  border: 1px solid var(--border-strong);
  background: transparent;
  color: var(--fg);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--t-fast);
}
.provider:hover {
  border-color: var(--fg);
  background: var(--bg-subtle);
}
.provider-next {
  margin-top: 16px;
}
.provider-note {
  margin: 8px 0 0;
  color: var(--fg-muted);
  font-size: 12px;
  line-height: 1.45;
}
.sep {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 28px 0 20px;
  color: var(--fg-muted);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.sep::before,
.sep::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
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
  padding: 12px 14px;
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
.login-submit {
  width: 100%;
  justify-content: center;
}
.login-sent {
  margin: 0 0 20px;
  font-size: 14px;
  line-height: 1.5;
  color: var(--fg);
}
.login-back {
  margin-top: 12px;
  padding-left: 0;
}
.login-foot {
  margin: 32px 0 0;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  color: var(--fg-muted);
  font-size: 12px;
  line-height: 1.5;
}
</style>
