<script setup lang="ts">
// Compact EN/FR language switch for the sidebar footer.
// Persists the choice and reloads so module-scope strings (nav, mappings,
// chart axis labels resolved via i18n.global.t at import time) re-render in
// the chosen language without per-call reactivity wiring.
import { SUPPORTED_LOCALES } from '@/plugins/i18n'
import { LocalStorageKey } from '@/utils/localStorage'
import { useI18n } from 'vue-i18n'

const { locale } = useI18n({ useScope: 'global' })

function setLocale(value: string): void {
  if (value === locale.value) return
  localStorage.setItem(LocalStorageKey.Locale, value)
  locale.value = value
  window.location.reload()
}
</script>

<template>
  <div class="lang-toggle" role="group" :aria-label="$t('shell.language')">
    <button
      v-for="l in SUPPORTED_LOCALES"
      :key="l.value"
      class="lang-btn"
      :class="{ 'is-active': locale === l.value }"
      :aria-pressed="locale === l.value"
      type="button"
      @click="setLocale(l.value)"
    >
      {{ l.label }}
    </button>
  </div>
</template>

<style scoped>
/* Handoff .ed-foot .lang: a plain switch with "/" separators; the active
   locale is red + bold, no background pill (brutalist — flat). */
.lang-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-sans);
  font-size: 11px;
  letter-spacing: 0.04em;
}
.lang-btn {
  font: inherit;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--fg-muted);
  cursor: pointer;
  transition: color var(--t-fast);
}
/* Slash divider between locales. */
.lang-btn:not(:last-child)::after {
  content: '/';
  margin-left: 6px;
  color: var(--fg-subtle);
  pointer-events: none;
}
.lang-btn:hover {
  color: var(--fg);
}
.lang-btn.is-active {
  color: var(--epfl-red);
  font-weight: 700;
}
</style>
