<script setup lang="ts">
/**
 * A viewer asks the admins for the contributor role (#248).
 *
 * Shown on the account page and on the "not open to your account" page. It
 * shows nothing to someone who already contributes. The state comes from
 * `user.access_request` on /auth/me: waiting, declined (ask again), or none.
 */
import { useAuthStore } from '@/stores/auth'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n({ useScope: 'global' })
const auth = useAuthStore()

const message = ref('')
const sending = ref(false)
const error = ref('')

const shown = computed(() => auth.isAuthenticated && !auth.hasRole('contributor'))
const request = computed(() => auth.user?.access_request ?? null)
const pending = computed(() => request.value?.status === 'pending')
const canAsk = computed(() => !!auth.user?.email && !!auth.user?.email_verified)

const sentOn = computed(() => {
  const iso = request.value?.created_at
  return iso ? new Date(iso).toLocaleDateString(locale.value, { dateStyle: 'long' }) : ''
})

async function send(): Promise<void> {
  if (sending.value) return
  sending.value = true
  error.value = ''
  try {
    await auth.requestAccess(message.value.trim())
    message.value = ''
  } catch (caught: unknown) {
    const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error.value = t(`auth.errors.${detail}`, t('auth.errors.generic'))
  } finally {
    sending.value = false
  }
}
</script>

<template>
  <section v-if="shown" class="access">
    <h2 class="t-panel">{{ $t('auth.access.title') }}</h2>
    <p class="access-lede">{{ $t('auth.access.lede') }}</p>

    <p v-if="pending" class="access-state">{{ $t('auth.access.pending', { date: sentOn }) }}</p>
    <p v-else-if="!canAsk" class="access-state">{{ $t('auth.access.no_email') }}</p>
    <form v-else class="access-form" @submit.prevent="send">
      <p v-if="request?.status === 'declined'" class="access-state">
        {{ $t('auth.access.declined') }}
      </p>
      <label class="access-label" for="access-message">{{ $t('auth.access.message_label') }}</label>
      <textarea
        id="access-message"
        v-model="message"
        class="access-message"
        rows="3"
        maxlength="2000"
        :placeholder="$t('auth.access.message_placeholder')"
      />
      <p v-if="error" class="access-error">{{ error }}</p>
      <button class="btn btn-primary btn-sm" type="submit" :disabled="sending">
        {{ sending ? $t('auth.access.sending') : $t('auth.access.send') }}
      </button>
    </form>
  </section>
</template>

<style scoped>
.access-lede {
  margin: 8px 0 16px;
  color: var(--fg-muted);
  font-size: 13px;
  line-height: 1.5;
  max-width: 60ch;
}
.access-state {
  margin: 0 0 16px;
  padding: 10px 12px;
  border-left: 3px solid var(--border-strong);
  background: var(--bg-subtle);
  font-size: 13px;
  line-height: 1.5;
}
.access-form {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}
.access-label {
  font-size: 12px;
  font-weight: 600;
}
.access-message {
  width: 100%;
  max-width: 60ch;
  padding: 8px 10px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  font-size: 13px;
  resize: vertical;
}
.access-message:focus {
  outline: 2px solid var(--fg);
  outline-offset: -1px;
}
.access-error {
  margin: 0;
  padding: 10px 12px;
  border-left: 3px solid var(--primary);
  background: var(--bg-subtle);
  font-size: 13px;
}
</style>
