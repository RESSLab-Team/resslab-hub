<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import type { CpIconName } from '@/components/contribute/icons'
import { useContributionStore } from '@/stores/contribution'
import { DATABASES } from '@/utils/navigation'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()

interface Flag {
  level: 'pass' | 'warn' | 'fail'
  icon: CpIconName
  title: string
  description?: string
  severity?: string
  category: string
}

const databaseName = computed(
  () => DATABASES.find((entry) => entry.id === store.database)?.name ?? ''
)

const canRun = computed(() => store.specimenId !== '')

/** Render one structured issue as "Row N: col='v' - message" for display. */
function issueText(issue: { row: number; column: string; value: string | null; message: string }) {
  if (issue.row === 0) return `${issue.column}: ${issue.message}`
  return `Row ${issue.row}: ${issue.column}='${issue.value ?? ''}' - ${issue.message}`
}

/**
 * The validator reports one structured result per file. Each error/warning
 * becomes its own flag so the counts match what the user has to fix.
 */
const flags = computed<Flag[]>(() => {
  const response = store.response
  if (!response) return []

  const result: Flag[] = []

  for (const file of response.results) {
    for (const issue of file.errors) {
      result.push({
        level: 'fail',
        icon: 'close',
        title: issueText(issue),
        severity: t('contribute.quality.severity_high'),
        category: `${t('contribute.quality.category_schema')} · ${file.file}`
      })
    }
    for (const issue of file.warnings) {
      result.push({
        level: 'warn',
        icon: 'alert',
        title: issueText(issue),
        severity: t('contribute.quality.severity_medium'),
        category: `${t('contribute.quality.category_file')} · ${file.file}`
      })
    }
    if (file.valid && file.warnings.length === 0) {
      result.push({
        level: 'pass',
        icon: 'check',
        title: t('contribute.quality.check_passed'),
        description: t('contribute.quality.check_passed_desc', { file: file.file }),
        category: t('contribute.quality.category_schema')
      })
    }
  }

  return result
})

const counts = computed(() => ({
  pass: flags.value.filter((flag) => flag.level === 'pass').length,
  warn: flags.value.filter((flag) => flag.level === 'warn').length,
  fail: flags.value.filter((flag) => flag.level === 'fail').length
}))
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
      <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 22px">
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
          {{ $t('contribute.quality.idle', { database: databaseName, id: store.specimenId }) }}
        </span>
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
        <span
          >{{ $t('contribute.quality.error') }} <code>{{ store.errorMessage }}</code></span
        >
      </div>

      <template v-else-if="store.response">
        <div class="cp-flagsum">
          <div class="fs pass">
            <b>{{ counts.pass }}</b>
            <span>{{ $t('contribute.quality.passed') }}</span>
          </div>
          <div class="fs warn">
            <b>{{ counts.warn }}</b>
            <span>{{ $t('contribute.quality.warnings') }}</span>
          </div>
          <div class="fs fail">
            <b>{{ counts.fail }}</b>
            <span>{{ $t('contribute.quality.failed') }}</span>
          </div>
        </div>

        <div v-for="(flag, index) in flags" :key="index" class="cp-flag" :class="flag.level">
          <div class="fmark"><cp-icon :size="13" :width="2.4" :name="flag.icon" /></div>
          <div class="fbody">
            <div class="ftitle">
              {{ flag.title }}
              <span
                v-if="flag.severity"
                class="fsev"
                :class="flag.level === 'fail' ? 'high' : 'med'"
              >
                {{ flag.severity }}
              </span>
            </div>
            <div v-if="flag.description" class="fdesc">{{ flag.description }}</div>
            <div class="fcat">{{ flag.category }}</div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>
