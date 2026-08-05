<script setup lang="ts">
import PageHeader from '@/components/commons/PageHeader.vue'
import ExperimentCards from '@/components/contribute/ExperimentCards.vue'
import { useContributionStore } from '@/stores/contribution'
import { useDictionaryStore } from '@/stores/dictionary'
import { CONTRIBUTION_DATABASES } from '@/utils/contribution'
import { DATABASES, type DatabaseId } from '@/utils/navigation'
import { loadContributor, saveContributor } from '@/utils/submission'
import {
  mdiAlertOutline,
  mdiBellOffOutline,
  mdiCheck,
  mdiCheckCircleOutline,
  mdiOpenInNew,
  mdiSend,
  mdiShieldCheckOutline
} from '@mdi/js'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()
const dictionary = useDictionaryStore()

onMounted(() => dictionary.fetch())

// Dev-only preview of the file-level problems panel. The editor always builds
// a well-formed archive, so a real check can never produce these from the UI —
// they come from schema drift, server faults, or the direct /validate path
// (see sample-data/global-issues). With `?demo=global-issues` in the URL, dev
// builds show a banner whose button injects the response such a batch gets,
// through the same mapping as a real check; any edit clears it. Dead code in
// production builds.
const demoMode =
  import.meta.env.DEV && new URLSearchParams(window.location.search).get('demo') === 'global-issues'

function injectDemoResponse(): void {
  const database = store.database
  if (!database) return
  const csvPath = CONTRIBUTION_DATABASES[database].csvPath
  const kinds = timeSeriesKindsFor(database)
  const orphanDir = kinds[0]?.directory ?? `${database}/measured_responses`
  store.response = {
    valid: false,
    message: 'Validation failed',
    error_count: 2,
    results: [
      {
        file: csvPath.split('/').pop()!,
        path: csvPath,
        valid: false,
        errors: [
          {
            row: 0,
            column: 'headers',
            value: null,
            message: 'Missing required columns: investigator'
          }
        ],
        warnings: [
          {
            row: 0,
            column: 'headers',
            value: null,
            message: 'Unexpected columns: unexpected_demo_column'
          }
        ]
      },
      {
        file: 'DEMO-ORPHAN.csv',
        path: `${orphanDir}/DEMO-ORPHAN.csv`,
        valid: false,
        errors: [
          {
            row: 0,
            column: 'id',
            value: 'DEMO-ORPHAN',
            message: "Foreign key 'DEMO-ORPHAN' not found in primary CSV"
          }
        ],
        warnings: []
      }
    ],
    error_results: [],
    valid_results: []
  }
  store.status = 'fail'
}

const supported = (id: DatabaseId) => CONTRIBUTION_DATABASES[id].qualityCheckSupported

// Switching database clears the batch, so when there is work to lose the first
// click only arms the button and the second one confirms.
const pending = ref<DatabaseId | null>(null)
const atRisk = computed(() => (store.hasAnyId ? store.experimentCount : 0))

function pick(id: DatabaseId): void {
  if (store.database === id) return
  if (atRisk.value > 0 && pending.value !== id) {
    pending.value = id
    return
  }
  pending.value = null
  store.selectDatabase(id)
}

/** One line summarizing the automatic server check. */
const statusText = computed(() => {
  switch (store.status) {
    case 'running':
      return t('contribute.status.running')
    case 'pass':
      return t('contribute.status.pass')
    case 'warn':
      return store.activeWarningCount > 0
        ? t('contribute.status.warn', { count: store.activeWarningCount })
        : t('contribute.status.warn_dismissed')
    case 'fail':
      return t('contribute.status.fail', { count: store.response?.error_count ?? 0 })
    case 'unsupported':
      return t('contribute.status.unsupported')
    case 'error':
      return `${t('contribute.status.error')} ${store.errorMessage}`
    default:
      return store.hasAnyId ? t('contribute.status.pending') : t('contribute.status.idle')
  }
})

/** Once every warning is dismissed the bar reads as a pass. */
const statusClass = computed(() =>
  store.status === 'warn' && store.activeWarningCount === 0 ? 'pass' : store.status
)

// --- Submission dialog ----------------------------------------------------

const dialogOpen = ref(false)
const contributor = ref(loadContributor())

const contributorValid = computed(
  () =>
    contributor.value.name.trim().length > 0 &&
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contributor.value.email.trim())
)

const curveCount = computed(() => Object.keys(store.timeSeries).length)

function openDialog(): void {
  contributor.value = loadContributor()
  dialogOpen.value = true
}

async function confirmSubmit(): Promise<void> {
  if (!contributorValid.value) return
  const details = {
    name: contributor.value.name.trim(),
    email: contributor.value.email.trim(),
    institution: contributor.value.institution.trim(),
    orcid: contributor.value.orcid.trim()
  }
  saveContributor(details)
  dialogOpen.value = false
  await store.submit(details)
}
</script>

<template>
  <div class="tool-page contribute-page">
    <page-header :eyebrow="$t('contribute.eyebrow')" :title="$t('contribute.title')">
      {{ $t('contribute.description') }}
    </page-header>

    <div class="tool-card setup">
      <div class="tool-card-h">{{ $t('contribute.setup.title') }}</div>
      <div class="db-grid">
        <button
          v-for="entry in DATABASES"
          :key="entry.id"
          class="db"
          :class="{ active: store.database === entry.id, pending: pending === entry.id }"
          type="button"
          @click="pick(entry.id)"
        >
          <v-icon :icon="entry.icon" size="17" />
          <span class="db-name">{{ entry.name }}</span>
          <span v-if="pending === entry.id" class="db-warn">
            {{ $t('contribute.setup.switch_confirm', { count: atRisk }) }}
          </span>
          <span v-else-if="!supported(entry.id)" class="db-flag">
            {{ $t('contribute.setup.no_check_badge') }}
          </span>
        </button>
      </div>
      <p v-if="store.config && !store.config.qualityCheckSupported" class="note">
        <v-icon :icon="mdiAlertOutline" size="14" />
        {{ $t('contribute.setup.no_quality_check') }}
      </p>
    </div>

    <template v-if="store.database">
      <p v-if="dictionary.state === 'loading' || dictionary.state === 'idle'" class="dict-state">
        {{ $t('contribute.dictionary_loading') }}
      </p>
      <p v-else-if="dictionary.state === 'error'" class="dict-state">
        {{ $t('contribute.dictionary_error') }}
        <button class="btn btn-secondary btn-sm" type="button" @click="dictionary.fetch()">
          {{ $t('contribute.retry') }}
        </button>
      </p>
      <experiment-cards v-else />

      <div v-if="demoMode && dictionary.ready" class="demo-banner">
        <span>Demo mode — preview problems the editor itself cannot produce.</span>
        <button
          class="btn btn-secondary btn-sm"
          data-testid="demo-inject"
          type="button"
          @click="injectDemoResponse()"
        >
          Inject file-level problems
        </button>
      </div>

      <div v-if="store.globalIssues.length" class="global-issues">
        <p class="global-issues-title">{{ $t('contribute.global_issues') }}</p>
        <p
          v-for="(entry, index) in store.globalIssues"
          :key="index"
          class="global-issue"
          :class="entry.severity"
        >
          <v-icon :icon="mdiAlertOutline" size="14" />
          {{ entry.issue.message }}
        </p>
      </div>
    </template>

    <footer
      v-if="store.database && dictionary.ready && store.submitStatus === 'submitted'"
      class="status-bar submitted-bar"
    >
      <span class="status pass">
        <v-icon :icon="mdiCheckCircleOutline" size="16" />
        {{ $t('contribute.submitted.title', { number: store.pullRequestNumber }) }}
      </span>
      <span class="submitted-note">{{ $t('contribute.submitted.next') }}</span>
      <span class="spacer" />
      <a class="btn btn-secondary btn-sm" :href="store.pullRequestUrl" target="_blank">
        <v-icon :icon="mdiOpenInNew" size="14" />{{ $t('contribute.submitted.view_pr') }}
      </a>
      <button class="btn btn-primary btn-sm" type="button" @click="store.reset()">
        {{ $t('contribute.submitted.new') }}
      </button>
    </footer>

    <footer v-else-if="store.database && dictionary.ready" class="status-bar">
      <span class="status" :class="statusClass">
        <v-icon
          :icon="
            statusClass === 'pass'
              ? mdiCheck
              : statusClass === 'running'
              ? mdiShieldCheckOutline
              : mdiAlertOutline
          "
          size="15"
        />
        {{ statusText }}
      </span>
      <span v-if="store.clientErrorCount" class="client-errors">
        {{ $t('contribute.status.client_errors', { count: store.clientErrorCount }) }}
      </span>
      <span v-if="store.dismissedCount" class="dismissed">
        <v-icon :icon="mdiBellOffOutline" size="14" />
        {{ $t('contribute.status.dismissed', { count: store.dismissedCount }) }}
        <button class="link" type="button" @click="store.restoreDismissed()">
          {{ $t('contribute.editor.restore_all') }}
        </button>
      </span>
      <span class="spacer" />
      <button
        class="btn btn-secondary btn-sm"
        :disabled="
          !store.hasAnyId || store.status === 'running' || !store.config?.qualityCheckSupported
        "
        type="button"
        @click="store.runQualityCheck()"
      >
        {{ $t('contribute.status.check_now') }}
      </button>
      <button
        class="btn btn-primary btn-sm"
        :disabled="!store.canSubmit"
        type="button"
        @click="openDialog()"
      >
        <v-icon :icon="mdiSend" size="14" />
        {{
          store.submitStatus === 'submitting'
            ? $t('contribute.submitting')
            : $t('contribute.submit')
        }}
      </button>
      <span v-if="store.submitStatus === 'error'" class="submit-error">
        {{ $t('contribute.submit_failed') }} {{ store.submitError }}
      </span>
      <span class="draft-note">{{ $t('contribute.draft_notice') }}</span>
    </footer>

    <div v-if="dialogOpen" class="dialog-backdrop" @click.self="dialogOpen = false">
      <div class="dialog tool-card" role="dialog" aria-modal="true">
        <div class="tool-card-h">{{ $t('contribute.dialog.title') }}</div>
        <p class="dialog-recap">
          {{
            $t('contribute.dialog.recap', {
              experiments: store.experimentCount,
              files: curveCount
            })
          }}
          <template v-if="store.dismissedWarningMessages.length">
            {{
              $t('contribute.dialog.recap_dismissed', {
                count: store.dismissedWarningMessages.length
              })
            }}
          </template>
        </p>
        <label class="dialog-field">
          <span>{{ $t('contribute.dialog.name') }} *</span>
          <input v-model="contributor.name" type="text" autocomplete="name" />
        </label>
        <label class="dialog-field">
          <span>{{ $t('contribute.dialog.email') }} *</span>
          <input v-model="contributor.email" type="email" autocomplete="email" />
        </label>
        <label class="dialog-field">
          <span>{{ $t('contribute.dialog.institution') }}</span>
          <input v-model="contributor.institution" type="text" autocomplete="organization" />
        </label>
        <label class="dialog-field">
          <span>{{ $t('contribute.dialog.orcid') }}</span>
          <input v-model="contributor.orcid" type="text" placeholder="0000-0000-0000-0000" />
        </label>
        <p class="dialog-note">{{ $t('contribute.dialog.note') }}</p>
        <div class="dialog-actions">
          <button class="btn btn-secondary btn-sm" type="button" @click="dialogOpen = false">
            {{ $t('contribute.dialog.cancel') }}
          </button>
          <button
            class="btn btn-primary btn-sm"
            :disabled="!contributorValid"
            type="button"
            @click="confirmSubmit()"
          >
            <v-icon :icon="mdiSend" size="14" />{{ $t('contribute.dialog.confirm') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.contribute-page {
  max-width: 1100px;
  padding: 24px clamp(16px, 4vw, 40px) 120px;
  margin: 0 auto;
}
.setup {
  margin-bottom: 20px;
}
.db-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.db {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  font-size: 13.5px;
  cursor: pointer;
  border-radius: var(--radius);
}
.db:hover {
  background: var(--bg-subtle);
  border-color: var(--fg-muted);
}
.db.active {
  border-color: var(--epfl-red);
  background: var(--epfl-red);
  color: #fff;
  font-weight: 600;
}
.db.pending {
  border-color: var(--epfl-orange);
}
.db-flag,
.db-warn {
  font-size: 11px;
  color: var(--epfl-orange);
}
.db.active .db-flag {
  color: #fff;
}
.db-warn {
  font-weight: 600;
}
.note {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 14px 0 0;
  font-size: 13px;
  color: var(--epfl-orange);
}
.dict-state {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--fg-muted);
}
.demo-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding: 10px 16px;
  border: 1px dashed var(--epfl-orange);
  font-size: 13px;
  color: var(--fg-muted);
}
.global-issues {
  margin-top: 16px;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-left: 3px solid var(--epfl-red);
  background: var(--bg);
}
.global-issues-title {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
}
.global-issue {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin: 3px 0;
  font-size: 13px;
}
.global-issue.error {
  color: var(--epfl-red);
}
.global-issue.warning {
  color: var(--epfl-orange);
}

.status-bar {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 20px;
  padding: 12px 16px;
  border: 1px solid var(--border);
  background: var(--bg);
  box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.06);
}
.status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
}
.status.pass {
  color: var(--epfl-green-text);
}
.status.warn {
  color: var(--epfl-orange);
}
.status.fail,
.status.error {
  color: var(--epfl-red);
}
.client-errors {
  font-size: 13px;
  color: var(--epfl-red);
}
.dismissed {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--fg-muted);
}
.dismissed .link {
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
  text-decoration: underline;
  cursor: pointer;
}
.dismissed .link:hover {
  color: var(--fg);
}
.spacer {
  flex: 1;
}
.draft-note {
  flex-basis: 100%;
  font-size: 12px;
  color: var(--fg-muted);
}
.submit-error {
  flex-basis: 100%;
  font-size: 13px;
  color: var(--epfl-red);
}
.submitted-bar {
  border-color: var(--epfl-green-text);
}
.submitted-note {
  font-size: 13px;
  color: var(--fg-muted);
}
.submitted-bar .btn {
  text-decoration: none;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.45);
}
.dialog {
  width: min(440px, 100%);
  max-height: 90vh;
  overflow-y: auto;
  background: var(--bg);
}
.dialog-recap {
  margin: 0 0 14px;
  font-size: 13.5px;
  color: var(--fg-muted);
}
.dialog-field {
  display: block;
  margin-bottom: 10px;
}
.dialog-field span {
  display: block;
  margin-bottom: 3px;
  font-size: 12.5px;
  font-weight: 600;
}
.dialog-field input {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  font-size: 13.5px;
  border-radius: var(--radius);
}
.dialog-field input:focus {
  outline: 2px solid var(--epfl-red);
  outline-offset: -1px;
}
.dialog-note {
  margin: 12px 0;
  font-size: 12px;
  color: var(--fg-muted);
}
.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
