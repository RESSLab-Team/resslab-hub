<script setup lang="ts">
import { fieldLabel } from '@/utils/contribution'
import { toExperimentRows, type ReviewBatch } from '@/utils/curation'
import type { DatabaseId } from '@/utils/navigation'
import {
  mapResponse,
  type QualityReport,
  type ReportedIssue,
  type Severity
} from '@/utils/qualityReport'
import type { ValidationIssue, ValidationResponse } from '@/utils/validationResponse'
import {
  mdiAlertOutline,
  mdiBellOffOutline,
  mdiCheck,
  mdiClose,
  mdiExclamationThick
} from '@mdi/js'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * The automated quality flags for a submission (prototype `.cp-flag` cards):
 * the same server-side checks the batch went through at submit time, re-run
 * against the current database and mapped back onto experiments.
 */
const props = defineProps<{
  database: DatabaseId
  /** The re-validation: of the pull request, or of live rows (#253). */
  loadValidation: () => Promise<ValidationResponse>
  detail: ReviewBatch
}>()
const emit = defineEmits<{
  (e: 'select', uid: number, column: string): void
}>()

const { t, te } = useI18n({ useScope: 'global' })

const state = ref<'loading' | 'ready' | 'error'>('loading')
const report = ref<QualityReport | null>(null)

watch(
  () => props.loadValidation,
  async (loadValidation) => {
    state.value = 'loading'
    report.value = null
    try {
      const response = await loadValidation()
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

function markIcon(severity: Severity): string {
  return severity === 'error' ? mdiClose : mdiExclamationThick
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
  <div>
    <p class="sech">{{ $t('curation.flags.title') }}</p>

    <p v-if="state === 'loading'" class="state">{{ $t('curation.flags.loading') }}</p>
    <p v-else-if="state === 'error'" class="state">
      <v-icon :icon="mdiAlertOutline" size="14" />
      {{ $t('curation.flags.unavailable') }}
    </p>

    <template v-else-if="report">
      <div class="flagsum">
        <div class="fs pass">
          <b>{{ summary.pass }}</b>
          <span>{{ $t('curation.flags.pass') }}</span>
        </div>
        <div class="fs warn">
          <b>{{ summary.warn }}</b>
          <span>{{ $t('curation.flags.warn') }}</span>
        </div>
        <div class="fs fail">
          <b>{{ summary.fail }}</b>
          <span>{{ $t('curation.flags.fail') }}</span>
        </div>
      </div>

      <p v-if="!hasIssues" class="allclear">
        <v-icon :icon="mdiCheck" size="14" />
        {{ $t('curation.flags.all_clear') }}
      </p>

      <template v-for="experiment in report.experiments" :key="experiment.uid">
        <div v-if="experiment.cellIssues.length || experiment.fileIssues.length" class="group">
          <p class="group-id">{{ experiment.id || `#${experiment.uid + 1}` }}</p>

          <button
            v-for="(entry, index) in experiment.cellIssues"
            :key="issueKey(entry, index)"
            class="flag click"
            :class="entry.severity"
            type="button"
            @click="emit('select', experiment.uid, entry.ref.column)"
          >
            <span class="fmark"><v-icon :icon="markIcon(entry.severity)" size="13" /></span>
            <span class="fbody">
              <span class="ftitle">
                {{ columnLabel(entry.ref.column) }}
                <span class="fsev" :class="entry.severity === 'error' ? 'high' : 'med'">
                  {{
                    entry.severity === 'error'
                      ? $t('curation.flags.high')
                      : $t('curation.flags.medium')
                  }}
                </span>
              </span>
              <span class="fdesc">{{ entry.issue.message }}</span>
              <span class="fcat">
                {{ $t('curation.flags.automated') }} ·
                {{ $t(`curation.flags.category.${category(entry.issue)}`) }}
              </span>
            </span>
          </button>

          <div
            v-for="(entry, index) in experiment.fileIssues"
            :key="`file-${issueKey(entry, index)}`"
            class="flag"
            :class="entry.severity"
          >
            <span class="fmark"><v-icon :icon="markIcon(entry.severity)" size="13" /></span>
            <span class="fbody">
              <span class="ftitle">
                {{ kindLabel(entry.kindKey) }}
                <span class="fsev" :class="entry.severity === 'error' ? 'high' : 'med'">
                  {{
                    entry.severity === 'error'
                      ? $t('curation.flags.high')
                      : $t('curation.flags.medium')
                  }}
                </span>
              </span>
              <span class="fdesc">{{ entry.issue.message }}</span>
              <span class="fcat">
                {{ $t('curation.flags.automated') }} · {{ $t('curation.flags.category.file') }}
              </span>
            </span>
          </div>
        </div>
      </template>

      <div v-if="report.global.length" class="group">
        <p class="group-id">{{ $t('curation.flags.global') }}</p>
        <div
          v-for="(entry, index) in report.global"
          :key="`global-${issueKey(entry, index)}`"
          class="flag"
          :class="entry.severity"
        >
          <span class="fmark"><v-icon :icon="markIcon(entry.severity)" size="13" /></span>
          <span class="fbody">
            <span class="ftitle">{{ entry.issue.column }}</span>
            <span class="fdesc">{{ entry.issue.message }}</span>
          </span>
        </div>
      </div>
    </template>

    <div v-if="detail.dismissed_warnings?.length" class="group">
      <p class="group-id">
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
.sech {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  margin: 0 0 14px;
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

/* ── summary strip (prototype .cp-flagsum) ── */
.flagsum {
  display: flex;
  border: 1px solid var(--border);
  margin-bottom: 18px;
}
.flagsum .fs {
  flex: 1;
  padding: 14px 8px;
  border-right: 1px solid var(--border);
  text-align: center;
}
.flagsum .fs:last-child {
  border-right: 0;
}
.flagsum .fs b {
  display: block;
  font-size: 24px;
  font-weight: 300;
  font-feature-settings: 'tnum';
}
.flagsum .fs span {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--fg-subtle);
  margin-top: 4px;
  display: block;
}
.flagsum .fs.pass b {
  color: var(--epfl-green-text);
}
.flagsum .fs.warn b {
  color: var(--epfl-orange);
}
.flagsum .fs.fail b {
  color: var(--epfl-red);
}
.allclear {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--epfl-green-text);
  margin: 4px 0;
}

/* ── groups ── */
.group {
  margin-top: 16px;
}
.group-id {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 0 0 2px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--fg-subtle);
}

/* ── flag cards (prototype .cp-flag) ── */
.flag {
  display: flex;
  gap: 13px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border-subtle);
  width: 100%;
  background: transparent;
  border-left: 0;
  border-right: 0;
  border-top: 0;
  color: var(--fg);
  font: inherit;
  text-align: left;
}
.flag.click {
  cursor: pointer;
}
.flag.click:hover .ftitle {
  color: var(--epfl-red);
}
.fmark {
  width: 20px;
  height: 20px;
  flex: 0 0 auto;
  border: 1px solid var(--border);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}
.flag.error .fmark {
  border-color: var(--epfl-red);
  color: var(--epfl-red);
}
.flag.warning .fmark {
  border-color: var(--epfl-orange);
  color: var(--epfl-orange);
}
.fbody {
  min-width: 0;
}
.ftitle {
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}
.fsev {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 1px 6px;
  border: 1px solid var(--border);
  color: var(--fg-muted);
  font-weight: 700;
}
.fsev.high {
  color: var(--epfl-red);
  border-color: var(--epfl-red);
}
.fsev.med {
  color: var(--epfl-orange);
  border-color: var(--epfl-orange);
}
.fdesc {
  display: block;
  font-size: 12px;
  color: var(--fg-muted);
  line-height: 1.5;
  margin-top: 4px;
}
.fcat {
  display: block;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--fg-subtle);
  margin-top: 6px;
}
.dismissed-item {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--fg-muted);
  line-height: 1.5;
}
</style>
