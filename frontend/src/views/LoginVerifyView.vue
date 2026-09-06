<script setup lang="ts">
/**
 * Where the mailed sign-in link lands (#247).
 *
 * The link carries the challenge and its token in the query, and this view
 * posts them. It is a page rather than a backend redirect on purpose: mail
 * scanners open every link in a message before the recipient does, and a GET
 * that signed someone in would hand them the account, or at least burn the
 * single-use token.
 */
import { useAuthStore } from '@/stores/auth'
import { mdiAlertCircleOutline } from '@mdi/js'
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'

const { t } = useI18n({ useScope: 'global' })
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const error = ref('')

function single(value: unknown): string {
  return Array.isArray(value) ? String(value[0] ?? '') : String(value ?? '')
}

onMounted(async () => {
  const challenge = single(route.query.challenge)
  const token = single(route.query.token)
  if (!challenge || !token) {
    error.value = t('auth.errors.invalid_or_expired')
    return
  }
  try {
    const target = await auth.verifyEmailLogin({ challenge, token })
    router.replace(target)
  } catch (caught: unknown) {
    const detail = (caught as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error.value = t(`auth.errors.${detail}`, t('auth.errors.generic'))
  }
})
</script>

<template>
  <div class="verify">
    <template v-if="error">
      <p class="verify-error">
        <v-icon :icon="mdiAlertCircleOutline" size="16" />
        <span>{{ error }}</span>
      </p>
      <router-link class="btn btn-primary btn-sm" :to="{ name: 'Login' }">
        {{ $t('auth.verify.try_again') }}
      </router-link>
    </template>
    <p v-else class="verify-wait">{{ $t('auth.verify.signing_in') }}</p>
  </div>
</template>

<style scoped>
.verify {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 16px;
  max-width: 460px;
  margin: 0 auto;
  padding: 64px 24px 96px;
}
.verify-error {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0;
  padding: 10px 12px;
  border-left: 3px solid var(--epfl-red);
  background: var(--bg-subtle);
  font-size: 13px;
  line-height: 1.45;
}
.verify-wait {
  margin: 0;
  color: var(--fg-muted);
  font-size: 14px;
}
</style>
