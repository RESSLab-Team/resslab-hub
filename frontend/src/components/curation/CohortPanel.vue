<script setup lang="ts">
import type { CurationDetail } from '@/backend'
import SimpleParallelChart from '@/components/commons/charts/SimpleParallelChart.vue'
import { GHOST_CONFIGS, requestFieldsFor } from '@/components/curation/ghost'
import ToolSwitch from '@/components/commons/tools/ToolSwitch.vue'
import { useDataset } from '@/composables/useDataset'
import { CONTRIBUTION_DATABASES, fieldLabel } from '@/utils/contribution'
import { cellValue, isMissing } from '@/utils/curation'
import type { DatabaseId } from '@/utils/navigation'
import { mdiAccountGroupOutline, mdiAlertOutline, mdiInformationOutline } from '@mdi/js'
import { computed, ref } from 'vue'

/**
 * Ghost mode (prototype "comparison with similar experiments" section): the
 * submitted specimen(s) drawn in red over the existing database (grey ghost
 * lines) on the same parallel-coordinates axes as the public dashboard,
 * introduced by a cohort banner that spells out the like-for-like criteria.
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
  <section v-if="config" class="cohort-section">
    <p class="sech">{{ $t('curation.cohort.title') }}</p>

    <p v-if="state === 'loading'" class="state">{{ $t('curation.cohort.loading') }}</p>
    <p v-else-if="state === 'error'" class="state">
      <v-icon :icon="mdiAlertOutline" size="14" />
      {{ $t('curation.cohort.unavailable') }}
    </p>

    <template v-else-if="chart">
      <div class="cohort">
        <div class="cohort-h">
          <v-icon :icon="mdiAccountGroupOutline" size="16" />
          <b>{{ $t('curation.cohort.banner_title') }}</b>
          <span class="ct">{{ $t('curation.cohort.count', { count: chart.cohortCount }) }}</span>
        </div>
        <p class="cohort-lead">{{ $t('curation.cohort.lead') }}</p>
        <div class="cohort-chips">
          <span v-for="entry in criteria" :key="entry.field">
            {{ entry.label }}: {{ entry.value }}
          </span>
        </div>
        <div class="cohort-foot">
          <tool-switch v-model="restrict" :label="$t('curation.cohort.restrict')" />
        </div>
        <p v-if="excluded.length && restrict" class="cohort-note">
          <v-icon :icon="mdiInformationOutline" size="14" />
          {{ $t('curation.cohort.excluded', { fields: excluded.join(', ') }) }}
        </p>
      </div>

      <div class="chartframe">
        <div class="ch">
          <span>{{ $t('curation.cohort.chart_title') }}</span>
          <span>
            {{
              $t('curation.cohort.ghosts', {
                count: chart.cohortCount,
                added: detail.experiments.length
              })
            }}
          </span>
        </div>
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
        <div class="chartleg">
          <span class="li">
            <span class="sw sel"></span>
            {{ $t('curation.cohort.legend_new', { id: selected?.id ?? '' }) }}
          </span>
          <span class="li">
            <span class="sw ghost"></span>
            {{ $t('curation.cohort.legend_ghost', { count: chart.cohortCount }) }}
          </span>
        </div>
        <p class="charthint">{{ $t('curation.cohort.hint') }}</p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.cohort-section {
  margin-top: 32px;
}
.sech {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.state {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0;
  font-size: 13.5px;
  color: var(--fg-muted);
}

/* ── cohort banner (prototype .cp-cohort) ── */
.cohort {
  border: 1px solid var(--border);
  border-left: 2px solid var(--fg);
  padding: 15px 18px;
  background: var(--bg-subtle);
}
.cohort-h {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 14px;
}
.cohort-h b {
  font-weight: 600;
}
.cohort-h .ct {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-subtle);
}
.cohort-lead {
  font-size: 13px;
  color: var(--fg-muted);
  line-height: 1.5;
  margin: 9px 0 12px;
}
.cohort-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.cohort-chips span {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.02em;
  padding: 4px 9px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
}
.cohort-foot {
  margin-top: 12px;
}
.cohort-note {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  font-size: 12px;
  color: var(--fg-subtle);
  margin: 12px 0 0;
  line-height: 1.45;
}

/* ── chart frame + legend (prototype .cp-previewchart / .cp-chartleg) ── */
.chartframe {
  border: 1px solid var(--border);
  padding: 16px 18px;
  margin-top: 16px;
}
.ch {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
  margin-bottom: 12px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.chartleg {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}
.chartleg .li {
  display: flex;
  align-items: center;
  gap: 7px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-muted);
}
.chartleg .sw {
  flex: 0 0 auto;
}
.chartleg .sw.sel {
  width: 12px;
  height: 12px;
  background: var(--epfl-red);
}
.chartleg .sw.ghost {
  width: 16px;
  height: 0;
  border-top: 2px solid var(--border-strong);
}
.charthint {
  font-size: 12.5px;
  color: var(--fg-muted);
  line-height: 1.5;
  margin: 12px 0 0;
}
</style>
