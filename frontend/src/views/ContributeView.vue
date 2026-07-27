<script setup lang="ts">
import PageHeader from '@/components/commons/PageHeader.vue'
import ExperimentCards from '@/components/contribute/ExperimentCards.vue'
import { useContributionStore } from '@/stores/contribution'
import { useDictionaryStore } from '@/stores/dictionary'
import { CONTRIBUTION_DATABASES } from '@/utils/contribution'
import { DATABASES, type DatabaseId } from '@/utils/navigation'
import { mdiAlertOutline, mdiBellOffOutline, mdiCheck, mdiSend, mdiShieldCheckOutline } from '@mdi/js'
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()
const dictionary = useDictionaryStore()

onMounted(() => dictionary.fetch())

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
      return store.hasAnyId
        ? t('contribute.status.pending')
        : t('contribute.status.idle')
  }
})

/** Once every warning is dismissed the bar reads as a pass. */
const statusClass = computed(() =>
  store.status === 'warn' && store.activeWarningCount === 0 ? 'pass' : store.status
)

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
    </template>

    <footer v-if="store.database && dictionary.ready" class="status-bar">
      <span class="status" :class="statusClass">
        <v-icon
          :icon="statusClass === 'pass' ? mdiCheck : statusClass === 'running' ? mdiShieldCheckOutline : mdiAlertOutline"
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
        :disabled="!store.hasAnyId || store.status === 'running' || !store.config?.qualityCheckSupported"
        type="button"
        @click="store.runQualityCheck()"
      >
        {{ $t('contribute.status.check_now') }}
      </button>
      <button class="btn btn-primary btn-sm" disabled type="button">
        <v-icon :icon="mdiSend" size="14" />{{ $t('contribute.submit') }}
      </button>
      <span class="draft-note">{{ $t('contribute.draft_notice') }}</span>
    </footer>
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
  align-items: baseline;
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
</style>
