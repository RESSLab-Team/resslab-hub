<script setup lang="ts">
import type { CurationDetail } from '@/backend'
import EyebrowText from '@/components/commons/EyebrowText.vue'
import ToolSegmented from '@/components/commons/tools/ToolSegmented.vue'
import CohortPanel from '@/components/curation/CohortPanel.vue'
import DataPreviewPanel from '@/components/curation/DataPreviewPanel.vue'
import MetadataPanel from '@/components/curation/MetadataPanel.vue'
import QualityFlagsRail from '@/components/curation/QualityFlagsRail.vue'
import { GHOST_CONFIGS } from '@/components/curation/ghost'
import { useDataset } from '@/composables/useDataset'
import { useCurationStore } from '@/stores/curation'
import { useDictionaryStore } from '@/stores/dictionary'
import { databaseIdForType, formatAge } from '@/utils/curation'
import { DATABASES } from '@/utils/navigation'
import {
  mdiAlertOutline,
  mdiArrowLeft,
  mdiCheck,
  mdiClose,
  mdiOpenInNew,
  mdiSendOutline
} from '@mdi/js'
import { computed, nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  prNumber: string
}>()

const { locale } = useI18n({ useScope: 'global' })
const store = useCurationStore()
const dictionary = useDictionaryStore()

const number = computed(() => Number(props.prNumber))
const detail = ref<CurationDetail | null>(null)
const state = ref<'loading' | 'ready' | 'error'>('loading')

const database = computed(() => (detail.value ? databaseIdForType(detail.value.type) : null))
const databaseName = computed(
  () => DATABASES.find((entry) => entry.id === database.value)?.name ?? detail.value?.type ?? ''
)

const selectedUid = ref(0)
const selected = computed(() => detail.value?.experiments[selectedUid.value])

const experimentItems = computed(
  () =>
    detail.value?.experiments.map((experiment, index) => ({
      value: String(index),
      text: experiment.id
    })) ?? []
)

const selectedFiles = computed(() => {
  if (!detail.value || !selected.value) return []
  return detail.value.files.filter(
    (file) => file.kind === 'timeseries' && file.experiment_id === selected.value?.id
  )
})

// "Existing range" ghost column: observed min–max of each numeric dictionary
// field across the database the submission targets (same dataset instance as
// the cohort panel — the module cache dedupes the fetch).
const ranges = ref<Record<string, { min: number; max: number }>>({})
async function loadRanges(): Promise<void> {
  const databaseId = database.value
  const config = databaseId ? GHOST_CONFIGS[databaseId] : undefined
  if (!databaseId || !config) return
  const dataset = useDataset<{ id: string }>(config.key, config.fetchAll)
  try {
    await dataset.ready()
  } catch {
    return
  }
  const numeric = new Set(['Numeric', 'DecimalFloat', 'SmallInteger', 'Integer', 'BigInteger'])
  const next: Record<string, { min: number; max: number }> = {}
  for (const column of dictionary.columnsFor(databaseId)) {
    if (!numeric.has(column.type)) continue
    const { data } = await dataset.getRange(column.name)
    const min = Number(data.min)
    const max = Number(data.max)
    // An all-zero range is `extent()`'s empty fallback — no signal, skip it.
    if (Number.isNaN(min) || Number.isNaN(max) || (min === 0 && max === 0)) continue
    next[column.name] = { min, max }
  }
  ranges.value = next
}

onMounted(async () => {
  dictionary.fetch()
  try {
    detail.value = await store.fetchDetail(number.value)
    state.value = 'ready'
    loadRanges()
  } catch {
    state.value = 'error'
  }
})

const metadataPanel = ref<InstanceType<typeof MetadataPanel> | null>(null)

/** A quality flag was clicked: show that experiment and flash the field. */
async function selectIssue(uid: number, column: string): Promise<void> {
  selectedUid.value = uid
  await nextTick()
  metadataPanel.value?.flash(column)
}
</script>

<template>
  <div class="tool-page review-page">
    <p v-if="state === 'loading'" class="state">{{ $t('curation.review.loading') }}</p>

    <template v-else-if="state === 'error'">
      <p class="state">
        <v-icon :icon="mdiAlertOutline" size="15" />
        {{ $t('curation.review.not_found') }}
      </p>
      <router-link class="btn btn-secondary btn-sm back" to="/curation">
        <v-icon :icon="mdiArrowLeft" size="14" />
        {{ $t('curation.review.back') }}
      </router-link>
    </template>

    <template v-else-if="detail && database">
      <div class="dash-head">
        <div class="eyebrow head-eyebrow">
          <eyebrow-text
            :text="`${$t('curation.review.eyebrow', {
              number: detail.pr_number
            })} · ${databaseName}`"
          />
          <span class="state-chip">{{ $t('curation.review.in_review') }}</span>
        </div>
        <div class="dash-head-row">
          <h1 class="dash-title">
            {{ detail.experiments[0]?.id ?? detail.title }}
            <span v-if="detail.experiments.length > 1" class="more">
              {{ $t('curation.review.more_experiments', { count: detail.experiments.length - 1 }) }}
            </span>
          </h1>
          <div class="dash-head-actions actions">
            <a
              class="btn btn-primary btn-sm"
              :href="detail.pr_url"
              target="_blank"
              rel="noreferrer"
            >
              <v-icon :icon="mdiOpenInNew" size="14" />
              {{ $t('curation.review.open_pr') }}
            </a>
            <span class="stub-actions" :title="$t('curation.actions.disabled_tooltip')">
              <button class="btn btn-secondary btn-sm" disabled type="button">
                <v-icon :icon="mdiCheck" size="14" />{{ $t('curation.actions.approve') }}
              </button>
              <button class="btn btn-secondary btn-sm" disabled type="button">
                <v-icon :icon="mdiClose" size="14" />{{ $t('curation.actions.reject') }}
              </button>
              <button class="btn btn-secondary btn-sm" disabled type="button">
                <v-icon :icon="mdiSendOutline" size="14" />
                {{ $t('curation.actions.request_changes') }}
              </button>
            </span>
          </div>
        </div>
        <p class="dash-desc">
          <template v-if="detail.contributor?.name">
            {{
              $t('curation.review.submitted_by', {
                name: detail.contributor.name
              })
            }}<template v-if="detail.contributor.institution">
              · {{ detail.contributor.institution }}</template
            >
            <template v-if="detail.contributor.orcid">
              · ORCID {{ detail.contributor.orcid }}</template
            >
          </template>
          <template v-else>{{ $t('curation.review.unknown_contributor') }}</template>
          · {{ formatAge(detail.submitted_at || detail.created_at, locale) }}
        </p>
      </div>

      <p v-if="detail.reconstruction_warning" class="reconstruction">
        <v-icon :icon="mdiAlertOutline" size="15" />
        {{ detail.reconstruction_warning }}
      </p>

      <tool-segmented
        v-if="experimentItems.length > 1"
        class="selector"
        :items="experimentItems"
        :model-value="String(selectedUid)"
        @update:model-value="selectedUid = Number($event)"
      />

      <div class="layout">
        <div class="main">
          <metadata-panel
            v-if="selected"
            ref="metadataPanel"
            :columns="detail.columns"
            :database="database"
            :experiment="selected"
            :ranges="ranges"
          />
          <data-preview-panel
            v-if="selected"
            :database="database"
            :files="selectedFiles"
            :pr-number="detail.pr_number"
          />
          <cohort-panel :database="database" :detail="detail" :selected-uid="selectedUid" />
        </div>

        <div class="rail">
          <quality-flags-rail
            :database="database"
            :detail="detail"
            :pr-number="detail.pr_number"
            @select="selectIssue"
          />
          <div class="tool-card notes">
            <div class="tool-card-h">{{ $t('curation.notes.title') }}</div>
            <p class="notes-text">{{ $t('curation.notes.on_github') }}</p>
            <a
              class="btn btn-secondary btn-sm"
              :href="detail.pr_url"
              target="_blank"
              rel="noreferrer"
            >
              <v-icon :icon="mdiOpenInNew" size="13" />
              {{ $t('curation.notes.open_discussion') }}
            </a>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.review-page {
  max-width: 1240px;
  padding: 24px clamp(16px, 4vw, 40px) 60px;
  margin: 0 auto;
}
.state {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--fg-muted);
}
.back {
  margin-top: 12px;
  text-decoration: none;
}
.head-eyebrow {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}
.state-chip {
  padding: 2px 8px;
  border: 1px solid var(--epfl-orange);
  border-radius: var(--radius);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--epfl-orange);
}
.more {
  margin-left: 8px;
  font-size: 14px;
  font-weight: 400;
  color: var(--fg-muted);
}
.actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.actions .btn {
  text-decoration: none;
}
.stub-actions {
  display: inline-flex;
  gap: 8px;
}
.stub-actions .btn[disabled] {
  cursor: not-allowed;
  opacity: 0.55;
}
.reconstruction {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
  padding: 10px 14px;
  border: 1px solid var(--epfl-orange);
  border-left-width: 3px;
  font-size: 13.5px;
  color: var(--epfl-orange);
}
.selector {
  margin-bottom: 16px;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  gap: 20px;
  align-items: start;
}
@media (max-width: 960px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
.main > * + * {
  margin-top: 20px;
}
.rail > * + * {
  margin-top: 20px;
}
.notes-text {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--fg-muted);
}
.notes .btn {
  text-decoration: none;
}
</style>
