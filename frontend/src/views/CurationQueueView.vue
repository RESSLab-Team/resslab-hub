<script setup lang="ts">
import ProgressLine from '@/components/commons/ProgressLine.vue'
import type { CurationSummary } from '@/backend'
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
  initials: string
}

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? '') + (parts[parts.length - 1]?.[0] ?? '')).toUpperCase() || '?'
}

const rows = computed<QueueRow[]>(() =>
  store.items.map((summary) => {
    const databaseId = databaseIdForType(summary.type)
    const database = DATABASES.find((entry) => entry.id === databaseId)
    return {
      summary,
      databaseName: database?.name ?? summary.type,
      initials: initialsOf(summary.contributor?.name ?? '')
    }
  })
)
</script>

<template>
  <div class="curation-page">
    <div class="phead">
      <p class="eyebrow">
        <span class="red">{{ $t('curation.eyebrow') }}</span>
        <span class="mut"> · {{ $t('curation.queue.eyebrow_qualifier') }}</span>
      </p>
      <div class="prow">
        <h1 class="ptitle">
          {{ $t('curation.queue.title') }}
          <span v-if="store.listState === 'ready' && store.configured" class="cnt">{{
            rows.length
          }}</span>
        </h1>
        <button
          v-if="store.listState === 'ready'"
          class="cp-btn"
          type="button"
          @click="store.fetchList(true)"
        >
          <v-icon :icon="mdiRefresh" size="14" />
          {{ $t('curation.queue.refresh') }}
        </button>
      </div>
      <p class="pdesc">{{ $t('curation.queue.description') }}</p>
    </div>

    <div class="pbody">
      <progress-line
        v-if="store.listState === 'loading' || store.listState === 'idle'"
        :active="true"
        :label="$t('curation.queue.loading')"
      />

      <p v-else-if="store.listState === 'error'" class="state">
        <v-icon :icon="mdiAlertOutline" size="15" />
        {{ $t('curation.queue.error') }}
        <button class="cp-btn" type="button" @click="store.fetchList(true)">
          {{ $t('curation.retry') }}
        </button>
      </p>

      <p v-else-if="!store.configured" class="state">
        <v-icon :icon="mdiAlertOutline" size="15" />
        {{ $t('curation.queue.not_configured') }}
      </p>

      <p v-else-if="rows.length === 0" class="state">
        {{ $t('curation.queue.empty') }}
      </p>

      <div v-else class="tablewrap">
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
            <tr
              v-for="row in rows"
              :key="row.summary.pr_number"
              class="click"
              @click="$router.push(`/curation/${row.summary.pr_number}`)"
            >
              <td class="id">#{{ row.summary.pr_number }}</td>
              <td>
                <span class="tag">{{ row.databaseName }}</span>
              </td>
              <td>
                <div class="nm">{{ row.summary.title }}</div>
                <div class="sub">{{ row.summary.branch }}</div>
              </td>
              <td>
                <div v-if="row.summary.contributor" class="userline">
                  <span class="ava">{{ row.initials }}</span>
                  <span>
                    <span class="un">{{ row.summary.contributor.name }}</span>
                    <span v-if="row.summary.contributor.institution" class="ue">{{
                      row.summary.contributor.institution
                    }}</span>
                  </span>
                </div>
                <span v-else class="mut">—</span>
              </td>
              <td class="num mono">{{ row.summary.experiment_count ?? '—' }}</td>
              <td class="mono mut">{{ formatAge(row.summary.updated_at, locale) }}</td>
              <td class="actions" @click.stop>
                <router-link class="rowlink" :to="`/curation/${row.summary.pr_number}`">
                  {{ $t('curation.queue.review') }} →
                </router-link>
                <a
                  class="ghlink"
                  :href="row.summary.pr_url"
                  target="_blank"
                  rel="noreferrer"
                  :title="$t('curation.queue.github')"
                >
                  <v-icon :icon="mdiOpenInNew" size="13" />
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.curation-page {
  min-height: 100%;
  background: var(--bg);
}

/* ── page head (prototype .cp-phead) ── */
.phead {
  padding: 30px clamp(20px, 3vw, 56px) 22px;
  border-bottom: 1px solid var(--fg);
}
.eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin: 0 0 14px;
}
.eyebrow .red {
  color: var(--epfl-red);
}
.eyebrow .mut {
  color: var(--fg-subtle);
}
.prow {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px 24px;
}
.ptitle {
  font-size: clamp(28px, 6vw, 40px);
  font-weight: 300;
  letter-spacing: -0.02em;
  line-height: 1;
  margin: 0;
}
.ptitle .cnt {
  font-size: 15px;
  font-weight: 400;
  color: var(--fg-muted);
  margin-left: 14px;
  font-feature-settings: 'tnum';
}
.pdesc {
  font-size: 14px;
  color: var(--fg-muted);
  line-height: 1.5;
  max-width: 74ch;
  margin: 16px 0 0;
}

/* ── prototype button (.cp-btn) ── */
.cp-btn {
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  padding: 10px 16px;
  border: 1px solid var(--fg);
  background: var(--bg);
  color: var(--fg);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  white-space: nowrap;
}
.cp-btn:hover {
  border-color: var(--epfl-red);
  color: var(--epfl-red);
}

.pbody {
  padding: 26px clamp(20px, 3vw, 56px) 50px;
}
.state {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--fg-muted);
}

/* ── table (prototype .cp-table) ── */
.tablewrap {
  border: 1px solid var(--border);
  overflow-x: auto;
}
.queue {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.queue thead th {
  text-align: left;
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-muted);
  font-weight: 700;
  padding: 12px 16px;
  border-bottom: 1px solid var(--fg);
  background: var(--bg-subtle);
  white-space: nowrap;
}
.queue th.num,
.queue td.num {
  text-align: right;
}
.queue tbody td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: middle;
}
.queue tbody tr:last-child td {
  border-bottom: 0;
}
.queue tbody tr:hover td {
  background: var(--bg-subtle);
}
.queue tbody tr:hover .nm {
  color: var(--epfl-red);
}
.queue tr.click {
  cursor: pointer;
}
.mono {
  font-family: var(--font-mono);
  font-size: 12px;
  font-feature-settings: 'tnum';
}
.mut {
  color: var(--fg-muted);
}
.id {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--fg-muted);
}
.tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 2px 7px;
  border: 1px solid var(--border);
  white-space: nowrap;
}
.nm {
  font-weight: 600;
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sub {
  font-family: var(--font-mono);
  font-weight: 400;
  font-size: 11px;
  color: var(--fg-subtle);
  margin-top: 2px;
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.userline {
  display: flex;
  align-items: center;
  gap: 11px;
}
.ava {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--fg);
  color: var(--bg);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}
.un {
  display: block;
  font-weight: 600;
}
.ue {
  display: block;
  font-size: 12px;
  color: var(--fg-subtle);
  margin-top: 1px;
}
.actions {
  white-space: nowrap;
  text-align: right;
}
.rowlink {
  color: var(--epfl-red);
  font-weight: 500;
  text-decoration: none;
}
.ghlink {
  margin-left: 12px;
  color: var(--fg-subtle);
}
.ghlink:hover {
  color: var(--epfl-red);
}
</style>
