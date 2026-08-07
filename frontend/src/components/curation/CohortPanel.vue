<script setup lang="ts">
import type { CurationDetail } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { GHOST_CONFIGS, requestFieldsFor } from '@/components/curation/ghost'
import ToolSwitch from '@/components/commons/tools/ToolSwitch.vue'
import { useDataset } from '@/composables/useDataset'
import { CONTRIBUTION_DATABASES, fieldLabel } from '@/utils/contribution'
import { cellValue, isMissing } from '@/utils/curation'
import type { DatabaseId } from '@/utils/navigation'
import { mdiAlertOutline } from '@mdi/js'
import { computed, ref } from 'vue'

/**
 * Ghost mode: the submitted specimen(s) drawn in red over the existing
 * database (grey ghost lines) on the same parallel-coordinates axes as the
 * public dashboard. Optionally restricted to a like-for-like cohort sharing
 * the submission's categorical key parameters.
 */
const props = defineProps<{
  database: DatabaseId
  detail: CurationDetail
  selectedUid: number
}>()

const config = GHOST_CONFIGS[props.database]

const state = ref<'loading' | 'ready' | 'error'>('loading')
const dataset = config ? useDataset<{ id: string }>(config.key, config.fetchAll) : null

// One-shot readiness: the dataset is cached for the session, so this resolves
// instantly on revisits (and pre-warms the public dashboard's charts).
const readyTick = ref(0)
dataset
  ?.ready()
  .then(() => {
    state.value = 'ready'
    readyTick.value++
  })
  .catch(() => {
    state.value = 'error'
  })

const restrict = ref(true)

const selected = computed(
  () => props.detail.experiments[props.selectedUid] ?? props.detail.experiments[0]
)

interface Criterion {
  field: string
  label: string
  value: string
}

/** Cohort criteria from the selected experiment; NR fields are excluded. */
const criteria = computed<Criterion[]>(() => {
  if (!config || !selected.value) return []
  return config.cohortFields
    .filter((field) => !isMissing(selected.value.cells[field]))
    .map((field) => ({
      field,
      label: fieldLabel(props.database, field),
      value: (selected.value.cells[field] ?? '').trim()
    }))
})

const excluded = computed(() => {
  if (!config || !selected.value) return []
  return config.cohortFields
    .filter((field) => isMissing(selected.value.cells[field]))
    .map((field) => fieldLabel(props.database, field))
})

// Exact set-membership per clause (trailing comma — see useParallelChart's
// changeSearches note): 'S355' must not also match 'S355J2'.
const cohortQuery = computed(() => {
  if (!restrict.value || !criteria.value.length) return undefined
  return criteria.value.map((entry) => `${entry.field}:${entry.value},`).join(';')
})

const requestFields = computed(() => (config ? requestFieldsFor(config.fields) : []))

const chart = computed(() => {
  if (!config || !dataset || state.value !== 'ready') return null
  void readyTick.value
  const cohort = dataset.matrixSync(requestFields.value, cohortQuery.value)
  const cohortIds = (cohort.ids ?? []) as string[]
  const cohortData = (cohort.data ?? []) as unknown as (string | number)[][]
  const submissionIds = props.detail.experiments.map((experiment) => experiment.id)
  const submissionData = props.detail.experiments.map((experiment) =>
    requestFields.value.map((field) => cellValue(experiment.cells[field]) as string | number)
  )
  return {
    ids: [...cohortIds, ...submissionIds],
    data: [...cohortData, ...submissionData],
    cohortCount: cohortIds.length,
    highlightIds: submissionIds
  }
})

const labelPrefix = computed(() => `${CONTRIBUTION_DATABASES[props.database].namespace}.`)
</script>

<template>
  <div v-if="config" class="tool-card">
    <div class="tool-card-h">{{ $t('curation.cohort.title') }}</div>

    <p v-if="state === 'loading'" class="state">{{ $t('curation.cohort.loading') }}</p>
    <p v-else-if="state === 'error'" class="state">
      <v-icon :icon="mdiAlertOutline" size="14" />
      {{ $t('curation.cohort.unavailable') }}
    </p>

    <template v-else-if="chart">
      <div class="cohort-bar">
        <tool-switch v-model="restrict" :label="$t('curation.cohort.restrict')" />
        <span class="count">{{ $t('curation.cohort.count', { count: chart.cohortCount }) }}</span>
      </div>

      <div v-if="restrict" class="chips">
        <span v-for="entry in criteria" :key="entry.field" class="chip">
          {{ entry.label }}: {{ entry.value }}
        </span>
        <span v-if="excluded.length" class="excluded">
          {{ $t('curation.cohort.excluded', { fields: excluded.join(', ') }) }}
        </span>
      </div>

      <p class="hint">{{ $t('curation.cohort.hint') }}</p>

      <simple-parallel-chart
        :animate="false"
        :data="chart.data"
        :fields="config.fields"
        :highlight-ids="chart.highlightIds"
        :ids="chart.ids"
        :is-filtered="false"
        :label-prefix="labelPrefix"
        :request-fields="requestFields"
      />
    </template>
  </div>
</template>

<style scoped>
.state {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0;
  font-size: 13.5px;
  color: var(--fg-muted);
}
.cohort-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.count {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--fg-muted);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.chip {
  padding: 2px 8px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  font-size: 12px;
}
.excluded {
  font-size: 12px;
  color: var(--fg-muted);
}
.hint {
  margin: 0 0 4px;
  font-size: 12.5px;
  color: var(--fg-muted);
}
</style>
