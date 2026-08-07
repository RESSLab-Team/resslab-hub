<script setup lang="ts">
import type { CurationDetail } from '@/backend'
import { useCurationStore } from '@/stores/curation'
import { fieldLabel } from '@/utils/contribution'
import { toExperimentRows } from '@/utils/curation'
import type { DatabaseId } from '@/utils/navigation'
import {
  mapResponse,
  type QualityReport,
  type ReportedIssue,
  type Severity
} from '@/utils/qualityReport'
import type { ValidationIssue } from '@/utils/validationResponse'
import {
  mdiAlertCircleOutline,
  mdiAlertOutline,
  mdiBellOffOutline,
  mdiCheckCircleOutline
} from '@mdi/js'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * The automated quality flags for a submission: the same server-side checks
 * the batch went through at submit time, re-run against the current database
 * and mapped back onto experiments (utils/qualityReport).
 */
const props = defineProps<{
  database: DatabaseId
  prNumber: number
  detail: CurationDetail
}>()
const emit = defineEmits<{
  (e: 'select', uid: number, column: string): void
}>()

const { t, te } = useI18n({ useScope: 'global' })
const store = useCurationStore()

const state = ref<'loading' | 'ready' | 'error'>('loading')
const report = ref<QualityReport | null>(null)

watch(
  () => props.prNumber,
  async (prNumber) => {
    state.value = 'loading'
    report.value = null
    try {
      const response = await store.fetchValidation(prNumber)
      report.value = mapResponse(props.database, toExperimentRows(props.detail), response)
      state.value = 'ready'
    } catch {
      state.value = 'error'
    }
  },
  { immediate: true }
)

const summary = computed(() => {
  const experiments = report.value?.experiments ?? []
  const globalIssues = report.value?.global ?? []
  return {
    pass: experiments.filter((entry) => entry.level === 'pass').length,
    warn: experiments.filter((entry) => entry.level === 'warn').length,
    fail:
      experiments.filter((entry) => entry.level === 'fail').length +
      (globalIssues.some((entry) => entry.severity === 'error') ? 1 : 0)
  }
})

/**
 * Lightweight category tag per issue, in the spirit of the #254 mockup
 * (schema / deduplication / statistical / format) — heuristic on purpose.
 */
function category(issue: ValidationIssue): string {
  if (issue.column === 'headers' || issue.column === 'file' || issue.column === 'row') {
    return 'schema'
  }
  if (/already exists|more than once/i.test(issue.message)) return 'deduplication'
  if (/outside the range/i.test(issue.message)) return 'statistical'
  return 'format'
}

function columnLabel(column: string): string {
  return fieldLabel(props.database, column)
}

function kindLabel(kindKey: string | null): string {
  const key = `contribute.timeseries.kind.${kindKey}`
  return kindKey && te(key) ? t(key) : t('curation.flags.file')
}

function severityIcon(severity: Severity): string {
  return severity === 'error' ? mdiAlertCircleOutline : mdiAlertOutline
}

const hasIssues = computed(() => {
  const value = report.value
  if (!value) return false
  return (
    value.global.length > 0 ||
    value.experiments.some((entry) => entry.cellIssues.length + entry.fileIssues.length > 0)
  )
})

function issueKey(entry: ReportedIssue, index: number): string {
  return `${entry.issue.row}-${entry.issue.column}-${index}`
}
</script>

<template>
  <div class="tool-card rail">
    <div class="tool-card-h">{{ $t('curation.flags.title') }}</div>

    <p v-if="state === 'loading'" class="state">{{ $t('curation.flags.loading') }}</p>
    <p v-else-if="state === 'error'" class="state">
      <v-icon :icon="mdiAlertOutline" size="14" />
      {{ $t('curation.flags.unavailable') }}
    </p>

    <template v-else-if="report">
      <p class="summary">
        <span class="chip pass">
          <v-icon :icon="mdiCheckCircleOutline" size="13" />
          {{ $t('curation.flags.pass', { count: summary.pass }) }}
        </span>
        <span class="chip warn">
          <v-icon :icon="mdiAlertOutline" size="13" />
          {{ $t('curation.flags.warn', { count: summary.warn }) }}
        </span>
        <span class="chip fail">
          <v-icon :icon="mdiAlertCircleOutline" size="13" />
          {{ $t('curation.flags.fail', { count: summary.fail }) }}
        </span>
      </p>

      <p v-if="!hasIssues" class="state pass-note">
        <v-icon :icon="mdiCheckCircleOutline" size="14" />
        {{ $t('curation.flags.all_clear') }}
      </p>

      <template v-for="experiment in report.experiments" :key="experiment.uid">
        <div v-if="experiment.cellIssues.length || experiment.fileIssues.length" class="experiment">
          <p class="experiment-id">{{ experiment.id || `#${experiment.uid + 1}` }}</p>

          <button
            v-for="(entry, index) in experiment.cellIssues"
            :key="issueKey(entry, index)"
            class="issue"
            :class="entry.severity"
            type="button"
            @click="emit('select', experiment.uid, entry.ref.column)"
          >
            <span class="issue-head">
              <v-icon :icon="severityIcon(entry.severity)" size="14" />
              <span class="issue-field">{{ columnLabel(entry.ref.column) }}</span>
              <span class="tag">{{ $t(`curation.flags.category.${category(entry.issue)}`) }}</span>
            </span>
            <span class="issue-message">{{ entry.issue.message }}</span>
          </button>

          <div
            v-for="(entry, index) in experiment.fileIssues"
            :key="`file-${issueKey(entry, index)}`"
            class="issue static"
            :class="entry.severity"
          >
            <span class="issue-head">
              <v-icon :icon="severityIcon(entry.severity)" size="14" />
              <span class="issue-field">{{ kindLabel(entry.kindKey) }}</span>
              <span class="tag">{{ $t('curation.flags.category.file') }}</span>
            </span>
            <span class="issue-message">{{ entry.issue.message }}</span>
          </div>
        </div>
      </template>

      <div v-if="report.global.length" class="experiment">
        <p class="experiment-id">{{ $t('curation.flags.global') }}</p>
        <div
          v-for="(entry, index) in report.global"
          :key="`global-${issueKey(entry, index)}`"
          class="issue static"
          :class="entry.severity"
        >
          <span class="issue-head">
            <v-icon :icon="severityIcon(entry.severity)" size="14" />
            <span class="issue-field">{{ entry.issue.column }}</span>
          </span>
          <span class="issue-message">{{ entry.issue.message }}</span>
        </div>
      </div>
    </template>

    <div v-if="detail.dismissed_warnings?.length" class="dismissed">
      <p class="experiment-id">
        <v-icon :icon="mdiBellOffOutline" size="13" />
        {{ $t('curation.flags.dismissed') }}
      </p>
      <p v-for="(warning, index) in detail.dismissed_warnings" :key="index" class="dismissed-item">
        {{ warning }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.rail {
  position: sticky;
  top: 16px;
}
.state {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0;
  font-size: 13.5px;
  color: var(--fg-muted);
}
.pass-note {
  color: var(--epfl-green-text);
}
.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 12px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  font-size: 12px;
  font-weight: 600;
}
.chip.pass {
  color: var(--epfl-green-text);
}
.chip.warn {
  color: var(--epfl-orange);
}
.chip.fail {
  color: var(--epfl-red);
}
.experiment {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.experiment-id {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 0 0 6px;
  font-size: 11.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
}
.issue {
  display: block;
  width: 100%;
  margin: 0 0 8px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  text-align: left;
  border-radius: var(--radius);
}
.issue:not(.static) {
  cursor: pointer;
}
.issue:not(.static):hover {
  background: var(--bg-subtle);
  border-color: var(--fg-muted);
}
.issue.error {
  border-left: 3px solid var(--epfl-red);
}
.issue.warning {
  border-left: 3px solid var(--epfl-orange);
}
.issue-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 3px;
}
.issue.error .issue-head {
  color: var(--epfl-red);
}
.issue.warning .issue-head {
  color: var(--epfl-orange);
}
.issue-field {
  font-size: 13px;
  font-weight: 600;
}
.tag {
  margin-left: auto;
  padding: 1px 6px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  font-size: 10.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
}
.issue-message {
  display: block;
  font-size: 12.5px;
  color: var(--fg-muted);
}
.dismissed {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.dismissed-item {
  margin: 0 0 4px;
  font-size: 12.5px;
  color: var(--fg-muted);
}
</style>
