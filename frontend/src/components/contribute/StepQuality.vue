<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useContributionStore } from '@/stores/contribution'
import { mapResponse, type ReportedIssue } from '@/utils/qualityReport'
import { DATABASES } from '@/utils/navigation'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()

const databaseName = computed(
  () => DATABASES.find((entry) => entry.id === store.database)?.name ?? ''
)

const canRun = computed(() => store.hasAnyId)

const report = computed(() =>
  store.database && store.response ? mapResponse(store.database, store.rows, store.response) : null
)

const summary = computed(() => {
  const experiments = report.value?.experiments ?? []
  return {
    pass: experiments.filter((e) => e.level === 'pass').length,
    warn: experiments.filter((e) => e.level === 'warn').length,
    fail: experiments.filter((e) => e.level === 'fail').length,
    global: report.value?.global.length ?? 0
  }
})

const problemExperiments = computed(
  () => report.value?.experiments.filter((e) => e.level !== 'pass') ?? []
)

function issueText(entry: ReportedIssue): string {
  const { issue } = entry
  if (issue.row === 0) return `${issue.column}: ${issue.message}`
  return `Row ${issue.row}: ${issue.column}='${issue.value ?? ''}' - ${issue.message}`
}

function kindLabel(kindKey: string | null): string {
  return kindKey ? t(`contribute.timeseries.kind.${kindKey}`) : t('contribute.quality.category_file')
}

/** Jump back to the grid and focus the offending cell. */
function goToCell(uid: number, column: string): void {
  store.requestFocus(uid, column)
  store.currentStep = 1
}
</script>

<template>
  <div>
    <div class="cp-wsectionlabel">
      {{ $t('contribute.wizard.step_label', { current: 4, total: 5 }) }}
    </div>
    <h2 class="cp-wh">{{ $t('contribute.quality.title') }}</h2>
    <p class="cp-wsub">{{ $t('contribute.quality.subtitle') }}</p>

    <p v-if="!store.database" class="cp-hint">
      {{ $t('contribute.metadata.select_database_first') }}
    </p>

    <template v-else>
      <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 16px">
        <button
          class="cp-btn primary"
          :disabled="!canRun || store.status === 'running'"
          type="button"
          @click="store.runQualityCheck()"
        >
          <cp-icon :size="15" name="shield" />
          {{
            store.status === 'running'
              ? $t('contribute.quality.running')
              : store.response
              ? $t('contribute.quality.rerun')
              : $t('contribute.quality.run')
          }}
        </button>
        <span v-if="!canRun" class="cp-hint" style="margin: 0">
          {{ $t('contribute.quality.no_id') }}
        </span>
        <span v-else-if="store.status === 'idle'" class="cp-hint" style="margin: 0">
          {{
            $t('contribute.quality.idle_multi', {
              database: databaseName,
              count: store.experimentCount
            })
          }}
        </span>
      </div>

      <div v-if="store.clientErrorCount > 0" class="cp-hint" style="margin-bottom: 14px">
        <cp-icon :size="13" name="alert" />
        {{ $t('contribute.quality.client_errors', { count: store.clientErrorCount }) }}
      </div>

      <div v-if="store.status === 'unsupported'" class="cp-eduflag">
        <cp-icon :size="15" name="info" />
        <span>{{ $t('contribute.quality.unsupported') }}</span>
      </div>

      <div
        v-else-if="store.status === 'error'"
        class="cp-eduflag"
        style="border-left-color: var(--epfl-red)"
      >
        <cp-icon :size="15" name="alert" />
        <span>{{ $t('contribute.quality.error') }} <code>{{ store.errorMessage }}</code></span>
      </div>

      <template v-else-if="report">
        <div class="cp-flagsum">
          <div class="fs pass">
            <b>{{ summary.pass }}</b>
            <span>{{ $t('contribute.quality.exp_passed') }}</span>
          </div>
          <div class="fs warn">
            <b>{{ summary.warn }}</b>
            <span>{{ $t('contribute.quality.exp_warned') }}</span>
          </div>
          <div class="fs fail">
            <b>{{ summary.fail }}</b>
            <span>{{ $t('contribute.quality.exp_failed') }}</span>
          </div>
        </div>

        <!-- One card per experiment with issues. -->
        <div v-for="exp in problemExperiments" :key="exp.uid" class="cp-exp" :class="exp.level">
          <div class="cp-exp-h">
            <span class="id">{{ exp.id || $t('contribute.quality.no_id_short') }}</span>
            <span class="cp-exp-badge" :class="exp.level">
              {{
                $t('contribute.quality.exp_issue_summary', {
                  fields: exp.cellIssues.length,
                  files: exp.fileIssues.length
                })
              }}
            </span>
          </div>
          <button
            v-for="(cell, i) in exp.cellIssues"
            :key="`c${i}`"
            class="cp-exp-issue"
            :class="cell.severity"
            type="button"
            @click="goToCell(cell.ref.uid, cell.ref.column)"
          >
            <cp-icon :size="13" :name="cell.severity === 'error' ? 'close' : 'alert'" />
            <span>{{ issueText(cell) }}</span>
            <cp-icon class="go" :size="13" name="arrowRight" />
          </button>
          <div
            v-for="(file, i) in exp.fileIssues"
            :key="`f${i}`"
            class="cp-exp-issue"
            :class="file.severity"
          >
            <cp-icon :size="13" :name="file.severity === 'error' ? 'close' : 'alert'" />
            <span>{{ kindLabel(file.kindKey) }} · {{ issueText(file) }}</span>
          </div>
        </div>

        <!-- File/header-level issues not tied to one experiment. -->
        <div v-if="report.global.length" class="cp-exp fail">
          <div class="cp-exp-h">
            <span class="id">{{ $t('contribute.quality.global_issues') }}</span>
          </div>
          <div
            v-for="(entry, i) in report.global"
            :key="`g${i}`"
            class="cp-exp-issue"
            :class="entry.severity"
          >
            <cp-icon :size="13" :name="entry.severity === 'error' ? 'close' : 'alert'" />
            <span>{{ issueText(entry) }}</span>
          </div>
        </div>

        <p v-if="summary.fail === 0 && summary.warn === 0" class="cp-hint ok" style="margin-top: 14px">
          <cp-icon :size="13" name="check" />{{ $t('contribute.quality.all_passed') }}
        </p>
      </template>
    </template>
  </div>
</template>
