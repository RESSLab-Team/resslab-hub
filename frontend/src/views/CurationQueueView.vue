<script setup lang="ts">
import type { CurationSummary } from '@/backend'
import PageHeader from '@/components/commons/PageHeader.vue'
import { useCurationStore } from '@/stores/curation'
import { databaseIdForType, formatAge } from '@/utils/curation'
import { DATABASES } from '@/utils/navigation'
import { mdiAlertOutline, mdiOpenInNew, mdiRefresh } from '@mdi/js'
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { locale } = useI18n({ useScope: 'global' })
const store = useCurationStore()
onMounted(() => store.fetchList())

interface QueueRow {
  summary: CurationSummary
  databaseName: string
  databaseIcon: string | undefined
}

const rows = computed<QueueRow[]>(() =>
  store.items.map((summary) => {
    const databaseId = databaseIdForType(summary.type)
    const database = DATABASES.find((entry) => entry.id === databaseId)
    return {
      summary,
      databaseName: database?.name ?? summary.type,
      databaseIcon: database?.icon
    }
  })
)
</script>

<template>
  <div class="tool-page curation-page">
    <page-header :eyebrow="$t('curation.eyebrow')" :title="$t('curation.queue.title')">
      {{ $t('curation.queue.description') }}
    </page-header>

    <p v-if="store.listState === 'loading' || store.listState === 'idle'" class="state">
      {{ $t('curation.queue.loading') }}
    </p>

    <p v-else-if="store.listState === 'error'" class="state">
      <v-icon :icon="mdiAlertOutline" size="15" />
      {{ $t('curation.queue.error') }}
      <button class="btn btn-secondary btn-sm" type="button" @click="store.fetchList(true)">
        {{ $t('curation.retry') }}
      </button>
    </p>

    <p v-else-if="!store.configured" class="state">
      <v-icon :icon="mdiAlertOutline" size="15" />
      {{ $t('curation.queue.not_configured') }}
    </p>

    <p v-else-if="rows.length === 0" class="state">
      {{ $t('curation.queue.empty') }}
      <button class="btn btn-secondary btn-sm" type="button" @click="store.fetchList(true)">
        <v-icon :icon="mdiRefresh" size="14" />
        {{ $t('curation.queue.refresh') }}
      </button>
    </p>

    <div v-else class="tool-card queue-card">
      <table class="queue">
        <thead>
          <tr>
            <th>{{ $t('curation.queue.headers.pr') }}</th>
            <th>{{ $t('curation.queue.headers.database') }}</th>
            <th>{{ $t('curation.queue.headers.title') }}</th>
            <th>{{ $t('curation.queue.headers.contributor') }}</th>
            <th class="num">{{ $t('curation.queue.headers.experiments') }}</th>
            <th>{{ $t('curation.queue.headers.updated') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.summary.pr_number">
            <td class="pr">#{{ row.summary.pr_number }}</td>
            <td>
              <span class="db-chip">
                <v-icon v-if="row.databaseIcon" :icon="row.databaseIcon" size="15" />
                {{ row.databaseName }}
              </span>
            </td>
            <td class="title-cell">{{ row.summary.title }}</td>
            <td>
              <template v-if="row.summary.contributor">
                {{ row.summary.contributor.name
                }}<span v-if="row.summary.contributor.institution" class="muted">
                  · {{ row.summary.contributor.institution }}</span
                >
              </template>
              <span v-else class="muted">—</span>
            </td>
            <td class="num">{{ row.summary.experiment_count ?? '—' }}</td>
            <td class="muted">{{ formatAge(row.summary.updated_at, locale) }}</td>
            <td class="actions">
              <router-link
                class="btn btn-primary btn-sm"
                :to="`/curation/${row.summary.pr_number}`"
              >
                {{ $t('curation.queue.review') }}
              </router-link>
              <a
                class="btn btn-secondary btn-sm"
                :href="row.summary.pr_url"
                target="_blank"
                rel="noreferrer"
              >
                <v-icon :icon="mdiOpenInNew" size="13" />
                {{ $t('curation.queue.github') }}
              </a>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.curation-page {
  max-width: 1100px;
  padding: 24px clamp(16px, 4vw, 40px) 60px;
  margin: 0 auto;
}
.state {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--fg-muted);
}
.queue-card {
  padding: 0;
  overflow-x: auto;
}
.queue {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
}
.queue th {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-strong);
  font-size: 11.5px;
  font-weight: 600;
  text-align: left;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-muted);
  white-space: nowrap;
}
.queue td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
.queue tbody tr:last-child td {
  border-bottom: none;
}
.queue tbody tr:hover {
  background: var(--bg-subtle);
}
.pr {
  font-weight: 600;
  white-space: nowrap;
}
.db-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  font-size: 12.5px;
  white-space: nowrap;
}
.title-cell {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.muted {
  color: var(--fg-muted);
}
.num {
  text-align: right;
}
.actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  white-space: nowrap;
}
.actions .btn {
  text-decoration: none;
}
</style>
