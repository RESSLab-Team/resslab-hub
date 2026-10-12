<script setup lang="ts">
import EyebrowText from '@/components/commons/EyebrowText.vue'
import MapMix from '@/components/map/MapMix.vue'
import { formatCount, type Counts } from '@/utils/mapSites'
import { useI18n } from 'vue-i18n'

/** The hover card of a marker. The parent places it next to the marker. */
defineProps<{
  kind: 'site' | 'cluster'
  eyebrow: string
  title: string
  n: number
  counts: Counts
  /** number of programs, sites only */
  programs?: number
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div class="mt" role="tooltip">
    <div class="mt-eye"><eyebrow-text :text="eyebrow" /></div>
    <div class="mt-title">{{ title }}</div>
    <div class="mt-n">
      <b>{{ formatCount(n) }}</b> {{ t('map.tests', n) }}
      <template v-if="programs !== undefined"> · {{ t('map.programs_count', programs) }}</template>
    </div>
    <map-mix :counts="counts" :max="4" />
    <div class="mt-foot">
      {{ kind === 'site' ? t('map.tip_open_site') : t('map.tip_open_cluster') }}
    </div>
  </div>
</template>

<style scoped>
.mt {
  position: absolute;
  z-index: 6;
  width: min(256px, calc(100vw - 32px));
  padding: 12px 14px 10px;
  background: var(--bg);
  color: var(--fg);
  border: 1px solid var(--fg);
  pointer-events: none;
}
.mt-eye {
  font-family: var(--title-eyebrow-font);
  font-size: var(--title-eyebrow-size);
  font-weight: var(--title-eyebrow-weight);
  letter-spacing: var(--title-eyebrow-tracking);
  text-transform: uppercase;
}
.mt-title {
  margin: 5px 0 3px;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.3;
  letter-spacing: -0.005em;
}
.mt-n {
  margin-bottom: 10px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-feature-settings: 'tnum';
  color: var(--fg-muted);
}
.mt-n b {
  color: var(--fg);
  font-weight: 600;
}
.mt-foot {
  margin-top: 9px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--fg-subtle);
}
</style>
