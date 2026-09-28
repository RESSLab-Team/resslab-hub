<script setup lang="ts">
/**
 * Signed in, but not allowed here (#247).
 *
 * Separate from the sign-in page on purpose: sending someone back to sign in
 * would suggest that signing in again would help, when what they need is a
 * role. #248 adds the "ask for access" form here.
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const needed = computed(() => {
  const value = route.query.need
  return Array.isArray(value) ? String(value[0] ?? '') : String(value ?? '')
})
</script>

<template>
  <div class="forbidden">
    <p class="eyebrow">{{ $t('auth.forbidden.eyebrow') }}</p>
    <h1 class="t-page">{{ $t('auth.forbidden.title') }}</h1>
    <p class="forbidden-lede">
      {{
        needed
          ? $t('auth.forbidden.needs_role', { role: $t(`auth.roles.${needed}`) })
          : $t('auth.forbidden.lede')
      }}
    </p>
    <p v-if="needed === 'contributor'" class="forbidden-hint">
      {{ $t('auth.forbidden.contributor_hint') }}
    </p>
    <router-link class="btn btn-secondary btn-sm" to="/">
      {{ $t('auth.forbidden.back_home') }}
    </router-link>
  </div>
</template>

<style scoped>
.forbidden-hint {
  margin: 0 0 24px;
  font-size: 14px;
  line-height: 21px;
  color: var(--fg-muted);
}

.forbidden {
  max-width: 560px;
  padding: 64px 32px 96px;
}
.forbidden-lede {
  margin: 12px 0 24px;
  color: var(--fg-muted);
  font-size: 14px;
  line-height: 1.5;
}
</style>
