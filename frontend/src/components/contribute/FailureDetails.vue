<script setup lang="ts">
import { useNotificationStore } from '@/stores/notification'
import { bugReportUrl, failureToMarkdown, type FailureReport } from '@/utils/failureReport'
import { mdiAlertCircleOutline, mdiBugOutline, mdiChevronRight, mdiContentCopy } from '@mdi/js'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * A failed request, as one line the contributor can unfold: the technical
 * details underneath, a copy button, and a link that opens a prefilled bug
 * issue on the hub's repository.
 */
const props = defineProps<{
  report: FailureReport
  /** Lead-in before the message, e.g. "The submission failed:". */
  label: string
}>()

const { t } = useI18n({ useScope: 'global' })
const notification = useNotificationStore()

const open = ref(false)
const issueUrl = computed(() => bugReportUrl(props.report))

const rows = computed(() => {
  const batch = [
    props.report.database,
    props.report.experiments !== undefined
      ? t('contribute.failure.experiments', { count: props.report.experiments })
      : '',
    props.report.files !== undefined
      ? t('contribute.failure.files', { count: props.report.files })
      : ''
  ]
    .filter(Boolean)
    .join(' · ')
  return [
    [t('contribute.failure.when'), props.report.at],
    [t('contribute.failure.request'), props.report.request ?? '—'],
    [t('contribute.failure.status'), props.report.status?.toString() ?? '—'],
    [t('contribute.failure.batch'), batch || '—']
  ]
})

async function copy(): Promise<void> {
  try {
    await navigator.clipboard.writeText(failureToMarkdown(props.report))
    notification.notify(t('contribute.failure.copied'))
  } catch {
    notification.notify(t('contribute.failure.copy_failed'))
  }
}
</script>

<template>
  <div class="failure">
    <p class="failure-line">
      <v-icon class="failure-icon" :icon="mdiAlertCircleOutline" size="15" />
      <span class="failure-text">
        {{ label }} {{ report.message }}
        <button class="failure-toggle" type="button" :aria-expanded="open" @click="open = !open">
          <v-icon class="chevron" :class="{ open }" :icon="mdiChevronRight" size="14" />
          {{ $t(open ? 'contribute.failure.hide_details' : 'contribute.failure.details') }}
        </button>
      </span>
    </p>
    <div v-if="open" class="failure-body">
      <dl class="failure-facts">
        <template v-for="[key, value] in rows" :key="key">
          <dt>{{ key }}</dt>
          <dd>{{ value }}</dd>
        </template>
      </dl>
      <pre v-if="report.response" class="failure-response">{{ report.response }}</pre>
      <div class="failure-actions">
        <a class="btn btn-secondary btn-sm" :href="issueUrl" target="_blank" rel="noreferrer">
          <v-icon :icon="mdiBugOutline" size="14" />{{ $t('contribute.failure.report') }}
        </a>
        <button class="btn btn-ghost btn-sm" type="button" @click="copy()">
          <v-icon :icon="mdiContentCopy" size="14" />{{ $t('contribute.failure.copy') }}
        </button>
        <span class="failure-hint">{{ $t('contribute.failure.report_hint') }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.failure {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: var(--epfl-red);
}
/* Icon pinned to the first line; the toggle flows after the message. */
.failure-line {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 0;
  line-height: 1.45;
}
.failure-icon {
  flex: none;
  margin-top: 2px;
}
.failure-text {
  flex: 1 1 auto;
  min-width: 0;
}
.failure-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 6px;
  padding: 0;
  vertical-align: baseline;
  border: none;
  background: transparent;
  font: inherit;
  font-size: 12.5px;
  color: var(--fg-muted);
  text-decoration: underline;
  cursor: pointer;
}
.failure-toggle:hover,
.failure-toggle:focus-visible {
  color: var(--fg);
}
.failure-toggle .chevron {
  transition: transform 0.15s ease;
}
.failure-toggle .chevron.open {
  transform: rotate(90deg);
}
.failure-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius);
  background: var(--bg-subtle);
  color: var(--fg);
}
.failure-facts {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 3px 14px;
  margin: 0;
  font-size: 12.5px;
}
.failure-facts dt {
  color: var(--fg-muted);
}
.failure-facts dd {
  margin: 0;
  overflow-wrap: anywhere;
  font-family: var(--font-mono);
}
.failure-response {
  max-height: 180px;
  overflow: auto;
  margin: 0;
  padding: 8px 10px;
  border: 1px solid var(--border-subtle);
  background: var(--bg);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.failure-actions {
  display: flex;
  align-items: center;
  gap: 8px 12px;
  flex-wrap: wrap;
}
.failure-actions .btn {
  text-decoration: none;
}
.failure-hint {
  font-size: 12px;
  color: var(--fg-muted);
}
</style>
