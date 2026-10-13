<script setup lang="ts">
/**
 * The "To verify" tab of the curation queue (#253): the rows that went live
 * unverified, one line per database and reference. A line opens its review
 * page, and its button opens the verification pull request on the data
 * repository straight away.
 */
import ProgressLine from '@/components/commons/ProgressLine.vue'
import type { Type, VerificationGroup, VerificationPull } from '@/backend'
import { errorDetail, useVerificationStore } from '@/stores/verification'
import { databaseIdForType } from '@/utils/curation'
import { idsSearch } from '@/utils/curationStatus'
import { DATABASES } from '@/utils/navigation'
import { mdiAlertOutline, mdiOpenInNew } from '@mdi/js'
import { computed, onMounted, ref } from 'vue'
import type { RouteLocationRaw } from 'vue-router'

const store = useVerificationStore()
onMounted(() => store.fetchList())

/** Ids shown in the row before "+n more". */
const PREVIEW = 4

interface Row {
  key: string
  group: VerificationGroup
  databaseName: string
  /** The dashboard filtered on these rows, when the database has one. */
  to: { path: string; query: Record<string, string> } | null
  /** The review page of the reference. */
  review: RouteLocationRaw
  preview: string
  more: number
}

const rows = computed<Row[]>(() =>
  store.groups.map((group) => {
    const databaseId = databaseIdForType(group.database)
    const database = DATABASES.find((entry) => entry.id === databaseId)
    return {
      key: `${group.database}|${group.reference}|${group.pending_pr?.pr_number ?? ''}`,
      group,
      databaseName: database?.name ?? group.database,
      to: database ? { path: database.to, query: { id: idsSearch(group.ids) } } : null,
      review: {
        name: 'VerificationReview',
        params: { type: group.database },
        query: { reference: group.reference }
      },
      preview: group.ids.slice(0, PREVIEW).join(', '),
      more: Math.max(0, group.ids.length - PREVIEW)
    }
  })
)

const busy = ref(new Set<string>())
const failures = ref(new Map<string, string>())

function pendingOf(row: Row): VerificationPull | undefined {
  return row.group.pending_pr ?? store.pendingFor(row.group.database, row.group.ids[0])
}

async function verify(row: Row): Promise<void> {
  busy.value = new Set(busy.value).add(row.key)
  const nextFailures = new Map(failures.value)
  nextFailures.delete(row.key)
  failures.value = nextFailures
  try {
    await store.verify(row.group.database as Type, row.group.ids)
  } catch (caught) {
    failures.value = new Map(failures.value).set(row.key, errorDetail(caught) ?? '')
  } finally {
    const next = new Set(busy.value)
    next.delete(row.key)
    busy.value = next
  }
}
</script>

<template>
  <div>
    <progress-line
      v-if="store.listState === 'loading' || store.listState === 'idle'"
      :active="true"
      :label="$t('curation.verify.loading')"
    />

    <p v-else-if="store.listState === 'error'" class="state">
      <v-icon :icon="mdiAlertOutline" size="15" />
      {{ $t('curation.verify.error') }}
      <button class="cp-btn" type="button" @click="store.fetchList(true)">
        {{ $t('curation.retry') }}
      </button>
    </p>

    <p v-else-if="rows.length === 0" class="state">
      {{ $t('curation.verify.empty') }}
    </p>

    <template v-else>
      <p v-if="!store.configured" class="state">
        <v-icon :icon="mdiAlertOutline" size="15" />
        {{ $t('curation.verify.not_configured') }}
      </p>
      <div class="tablewrap">
        <table class="queue">
          <thead>
            <tr>
              <th>{{ $t('curation.queue.headers.database') }}</th>
              <th>{{ $t('curation.verify.headers.reference') }}</th>
              <th class="num">{{ $t('curation.queue.headers.experiments') }}</th>
              <th>{{ $t('curation.verify.headers.ids') }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.key" class="click" @click="$router.push(row.review)">
              <td>
                <span class="tag">{{ row.databaseName }}</span>
              </td>
              <td>
                <div class="nm" :title="row.group.reference">
                  {{ row.group.reference || $t('curation.verify.no_reference') }}
                </div>
              </td>
              <td class="num mono">{{ row.group.count }}</td>
              <td @click.stop>
                <router-link v-if="row.to" class="ids mono" :to="row.to">
                  {{ row.preview }}
                  <span v-if="row.more > 0" class="mut">{{
                    $t('curation.verify.more', { count: row.more }, row.more)
                  }}</span>
                </router-link>
                <span v-else class="ids mono">{{ row.preview }}</span>
              </td>
              <td class="actions" @click.stop>
                <router-link class="rowlink" :to="row.review">
                  {{ $t('curation.queue.review') }} →
                </router-link>
                <a
                  v-if="pendingOf(row)"
                  class="ghlink pending"
                  :href="pendingOf(row)?.pr_url"
                  target="_blank"
                  rel="noreferrer"
                >
                  {{ $t('commons.unverified.pending', { number: pendingOf(row)?.pr_number }) }}
                  <v-icon :icon="mdiOpenInNew" size="13" />
                </a>
                <button
                  v-else
                  class="cp-btn"
                  type="button"
                  :disabled="!store.configured || busy.has(row.key)"
                  @click="verify(row)"
                >
                  {{
                    busy.has(row.key)
                      ? $t('commons.unverified.opening')
                      : $t('curation.verify.button', { count: row.group.count }, row.group.count)
                  }}
                </button>
                <div v-if="failures.has(row.key)" class="fail" role="alert">
                  {{ $t('commons.unverified.failed') }}
                  <span v-if="failures.get(row.key)" class="mut">{{ failures.get(row.key) }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="note">{{ $t('curation.verify.note') }}</p>
    </template>
  </div>
</template>

<style scoped>
/* The same table as the review queue (views/CurationQueueView.vue). */
.state {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--fg-muted);
}
.state + .tablewrap {
  margin-top: 16px;
}
.cp-btn {
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  padding: 8px 14px;
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
.cp-btn:disabled {
  opacity: 0.4;
  pointer-events: none;
}
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
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ids {
  color: var(--fg);
  text-decoration: none;
  border-bottom: 1px solid var(--border);
}
a.ids:hover {
  color: var(--link-hover);
  border-bottom-color: var(--link-hover);
}
.actions {
  white-space: nowrap;
  text-align: right;
}
.rowlink {
  color: var(--epfl-red);
  font-weight: 500;
  text-decoration: none;
  margin-right: 14px;
}
.ghlink {
  color: var(--fg-muted);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ghlink:hover {
  color: var(--epfl-red);
}
.fail {
  margin-top: 6px;
  font-size: 12px;
  white-space: normal;
  max-width: 320px;
  margin-left: auto;
  text-align: left;
}
.fail .mut {
  display: block;
}
.note {
  font-size: 12px;
  color: var(--fg-muted);
  line-height: 1.5;
  max-width: 74ch;
  margin: 14px 0 0;
}
</style>
