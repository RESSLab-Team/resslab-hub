<script setup lang="ts">
import PageHeader from '@/components/commons/PageHeader.vue'
import ToolSelect from '@/components/commons/tools/ToolSelect.vue'
import ExperimentCards from '@/components/contribute/ExperimentCards.vue'
import { useContributionStore } from '@/stores/contribution'
import { useDictionaryStore } from '@/stores/dictionary'
import { DATABASES } from '@/utils/navigation'
import type { DatabaseId } from '@/utils/navigation'
import { mdiAlertOutline, mdiCheck, mdiSend, mdiShieldCheckOutline } from '@mdi/js'
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()
const dictionary = useDictionaryStore()

onMounted(() => dictionary.fetch())

const databaseItems = computed(() =>
  DATABASES.map((entry) => ({ title: entry.name, value: entry.id }))
)

function onDatabase(value: string): void {
  if (value) store.selectDatabase(value as DatabaseId)
}

/** One line summarizing the automatic server check. */
const statusText = computed(() => {
  switch (store.status) {
    case 'running':
      return t('contribute.status.running')
    case 'pass':
      return t('contribute.status.pass')
    case 'warn':
      return t('contribute.status.warn', { count: warningCount.value })
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

const warningCount = computed(
  () =>
    store.response?.results.reduce((total, file) => total + file.warnings.length, 0) ?? 0
)
</script>

<template>
  <div class="tool-page contribute-page">
    <page-header :eyebrow="$t('contribute.eyebrow')" :title="$t('contribute.title')">
      {{ $t('contribute.description') }}
    </page-header>

    <div class="tool-card setup">
      <div class="tool-card-h">{{ $t('contribute.setup.title') }}</div>
      <div class="setup-grid">
        <div class="tfield">
          <div class="tfield-label">{{ $t('contribute.setup.database') }}</div>
          <tool-select
            :items="databaseItems"
            :model-value="store.database ?? ''"
            :placeholder="$t('contribute.setup.database_placeholder')"
            @update:model-value="onDatabase"
          />
        </div>
        <div class="tfield">
          <div class="tfield-label">{{ $t('contribute.setup.program') }}</div>
          <input v-model="store.program" class="tinput" type="text" />
        </div>
        <div class="tfield">
          <div class="tfield-label">{{ $t('contribute.setup.year') }}</div>
          <input v-model="store.year" class="tinput" type="text" />
        </div>
        <div class="tfield">
          <div class="tfield-label">{{ $t('contribute.setup.doi') }}</div>
          <input v-model="store.doi" class="tinput" type="text" />
        </div>
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
      <span class="status" :class="store.status">
        <v-icon
          :icon="store.status === 'pass' ? mdiCheck : store.status === 'running' ? mdiShieldCheckOutline : mdiAlertOutline"
          size="15"
        />
        {{ statusText }}
      </span>
      <span v-if="store.clientErrorCount" class="client-errors">
        {{ $t('contribute.status.client_errors', { count: store.clientErrorCount }) }}
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
.setup-grid {
  display: grid;
  grid-template-columns: 2fr 2fr 1fr 2fr;
  gap: 16px;
}
@media (max-width: 800px) {
  .setup-grid {
    grid-template-columns: 1fr;
  }
}
.tinput {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--fg);
  font: inherit;
  font-size: 14px;
  border-radius: var(--radius);
}
.tinput:focus {
  outline: 2px solid var(--epfl-red);
  outline-offset: -1px;
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
.spacer {
  flex: 1;
}
.draft-note {
  flex-basis: 100%;
  font-size: 12px;
  color: var(--fg-muted);
}
</style>
