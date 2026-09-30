<script setup lang="ts">
import type { MapProgram } from '@/backend'
import { isHttpUrl } from '@/utils/common'
import { categoryFor, colorFor, routeFor } from '@/utils/mapCategories'
import { figureLabel, formatCount, programImage } from '@/utils/mapSites'
import { mdiArrowRight, mdiChevronDown, mdiOpenInNew } from '@mdi/js'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

/** One experimental program of a site, as an accordion row. */
const props = defineProps<{ program: MapProgram; open: boolean }>()
const emit = defineEmits<{ toggle: [] }>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()

const category = computed(() => categoryFor(props.program.category))
const figure = computed(() => figureLabel(props.program))
const image = computed(() => programImage(props.program))
const publication = computed(() => (isHttpUrl(props.program.link) ? props.program.link : null))
const bodyId = computed(() => `mp-${props.program.category}-${props.program.first_id}`)

// The database pages open the detail drawer of `id` when `detail=true`.
function openData() {
  router.push({
    path: routeFor(props.program.category),
    query: { id: props.program.first_id, detail: 'true' }
  })
}
</script>

<template>
  <div class="mp" :class="{ 'is-open': open }">
    <button
      class="mp-h"
      type="button"
      :aria-expanded="open"
      :aria-controls="bodyId"
      @click="emit('toggle')"
    >
      <span class="mp-sq" :style="{ background: colorFor(program.category) }"></span>
      <span class="mp-t">
        <span class="mp-ref">
          {{ program.program }}
          <span v-if="program.year" class="mp-year">({{ program.year }})</span>
        </span>
        <span class="mp-sub">
          {{ t(category.labelKey) }}<template v-if="figure"> · {{ figure }}</template>
        </span>
      </span>
      <span class="mp-n">{{ formatCount(program.n) }}</span>
      <v-icon class="mp-c" :icon="mdiChevronDown" size="14" />
    </button>
    <div v-if="open" :id="bodyId" class="mp-b">
      <div v-if="image" class="mp-img">
        <img :src="image" :alt="t(category.altKey)" loading="lazy" />
      </div>
      <div class="mp-kv">
        <div>
          <span>{{ t('map.database') }}</span
          ><span>{{ t(category.labelKey) }}</span>
        </div>
        <div v-if="figure">
          <span>{{ t('map.configuration') }}</span
          ><span>{{ figure }}</span>
        </div>
        <div v-if="program.year">
          <span>{{ t('map.year') }}</span
          ><span>{{ program.year }}</span>
        </div>
        <div>
          <span>{{ t('map.specimens') }}</span
          ><span>{{ formatCount(program.n) }}</span>
        </div>
      </div>
      <p v-if="program.reference" class="mp-cite">{{ program.reference }}</p>
      <div class="mp-a">
        <button class="btn btn-primary btn-sm" type="button" @click="openData">
          {{ t('map.view_experimental_data') }}
          <v-icon :icon="mdiArrowRight" size="14" />
        </button>
        <a v-if="publication" class="mp-link" :href="publication" target="_blank" rel="noreferrer">
          {{ t('map.publication') }}
          <v-icon :icon="mdiOpenInNew" size="12" />
        </a>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mp {
  border-bottom: 1px solid var(--border-subtle);
}
.mp-h {
  width: 100%;
  display: grid;
  grid-template-columns: 11px minmax(0, 1fr) auto 14px;
  gap: 11px;
  align-items: center;
  padding: 12px var(--mp-pad, 22px);
  border: 0;
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.mp-h:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: -2px;
}
.mp-sq {
  width: 11px;
  height: 11px;
}
.mp-t {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.mp-ref {
  font-size: 13.5px;
  transition: color var(--t-fast);
}
.mp-h:hover .mp-ref {
  color: var(--primary);
}
.mp-year {
  color: var(--fg-subtle);
}
.mp-sub {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--fg-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mp-n {
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-feature-settings: 'tnum';
}
.mp-c {
  color: var(--fg-subtle);
  transition: transform var(--t-fast);
}
.is-open .mp-c {
  transform: rotate(180deg);
  color: var(--fg);
}
.is-open .mp-h,
.mp-b {
  background: var(--bg-subtle);
}
.mp-b {
  padding: 4px var(--mp-pad, 22px) 18px;
}
.mp-img {
  height: 128px;
  margin-bottom: 12px;
  padding: 10px;
  background: var(--bg);
  border: 1px solid var(--border);
}
/* The img fills the box and object-fit scales the drawing inside it. The
   box was a grid before, and a max-height in % does nothing on a grid item
   in an auto row, so most drawings went past the box. */
.mp-img img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.mp-kv > div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 7px 0;
  border-top: 1px solid var(--border);
  font-size: 12px;
}
.mp-kv > div span:first-child {
  padding-top: 2px;
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-subtle);
}
.mp-kv > div span:last-child {
  font-family: var(--font-mono);
  font-size: 11.5px;
  text-align: right;
}
.mp-cite {
  margin: 10px 0 0;
  font-size: 11.5px;
  line-height: 1.45;
  color: var(--fg-muted);
}
.mp-a {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
}
.mp-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--fg);
  transition: color var(--t-fast);
}
.mp-link:hover {
  color: var(--primary);
}
</style>
