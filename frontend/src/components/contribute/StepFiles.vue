<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useContributionStore } from '@/stores/contribution'
import { checkTimeSeriesFile, timeSeriesKindsFor, type TimeSeriesKind } from '@/utils/timeseries'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()

const kinds = computed(() => timeSeriesKindsFor(store.database))

/** Experiments that can receive files: those with a non-empty id. */
const experiments = computed(() =>
  store.rows
    .map((row) => ({ uid: row.uid, id: (row.cells.id ?? '').trim() }))
    .filter((row) => row.id !== '')
)
const idlessCount = computed(() => store.rows.length - experiments.value.length)

const inputs = ref<Record<string, HTMLInputElement | null>>({})
const dragKey = ref('')
const errors = ref<Record<string, string>>({})
/** Per-kind report of a bulk drop: which stems matched, which did not. */
const bulkReport = ref<Record<string, { attached: number; unmatched: string[] }>>({})

function describeCheck(kind: TimeSeriesKind, text: string): { rows: number } | { error: string } {
  const result = checkTimeSeriesFile(kind, text)
  if (result.ok) return { rows: result.rows }
  if (result.error === 'empty') return { error: t('contribute.timeseries.error_empty') }
  return { error: t('contribute.timeseries.error_columns', { columns: result.missing.join(', ') }) }
}

async function attachOne(uid: number, kind: TimeSeriesKind, file: File): Promise<boolean> {
  const text = await file.text()
  const check = describeCheck(kind, text)
  if ('error' in check) {
    errors.value[`${uid}:${kind.key}`] = check.error
    return false
  }
  delete errors.value[`${uid}:${kind.key}`]
  store.timeSeries[`${uid}:${kind.key}`] = { name: file.name, content: text, rows: check.rows }
  store.resetQualityCheck()
  return true
}

/** Bulk drop: match each file's stem (case-sensitive) to an experiment id. */
async function bulkAttach(kind: TimeSeriesKind, files: FileList | undefined): Promise<void> {
  if (!files) return
  const byId = new Map(experiments.value.map((row) => [row.id, row.uid]))
  let attached = 0
  const unmatched: string[] = []
  for (const file of Array.from(files)) {
    const stem = file.name.replace(/\.csv$/i, '')
    const uid = byId.get(stem)
    if (uid === undefined) {
      unmatched.push(file.name)
      continue
    }
    if (await attachOne(uid, kind, file)) attached++
  }
  bulkReport.value[kind.key] = { attached, unmatched }
}

function onBulkDrop(kind: TimeSeriesKind, event: DragEvent): void {
  dragKey.value = ''
  bulkAttach(kind, event.dataTransfer?.files ?? undefined)
}

function onBulkSelect(kind: TimeSeriesKind, event: Event): void {
  const input = event.target as HTMLInputElement
  bulkAttach(kind, input.files ?? undefined)
  input.value = ''
}

function onSlotSelect(uid: number, kind: TimeSeriesKind, event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) attachOne(uid, kind, file)
  input.value = ''
}

function remove(uid: number, kind: TimeSeriesKind): void {
  delete store.timeSeries[`${uid}:${kind.key}`]
  delete errors.value[`${uid}:${kind.key}`]
  store.resetQualityCheck()
}
</script>

<template>
  <div>
    <div class="cp-wsectionlabel">
      {{ $t('contribute.wizard.step_label', { current: 3, total: 5 }) }}
    </div>
    <h2 class="cp-wh">{{ $t('contribute.files.title') }}</h2>
    <p class="cp-wsub">{{ $t('contribute.files.subtitle') }}</p>

    <p v-if="!store.database" class="cp-hint">
      {{ $t('contribute.metadata.select_database_first') }}
    </p>

    <template v-else-if="kinds.length === 0">
      <div class="cp-eduflag">
        <cp-icon :size="15" name="info" />
        <span>{{ $t('contribute.timeseries.none_for_database') }}</span>
      </div>
    </template>

    <template v-else-if="experiments.length === 0">
      <div class="cp-eduflag" style="border-left-color: var(--epfl-orange)">
        <cp-icon :size="15" name="alert" />
        <span>{{ $t('contribute.timeseries.needs_id') }}</span>
      </div>
    </template>

    <template v-else>
      <!-- Bulk attach: drop many files at once, matched to experiments by name. -->
      <div class="cp-fieldset">
        <div class="cp-fset-h">
          {{ $t('contribute.timeseries.bulk_title') }}
          <span class="ct">{{ $t('contribute.timeseries.bulk_hint') }}</span>
        </div>
        <div class="cp-fset-body">
          <div v-for="kind in kinds" :key="kind.key" class="cp-ts-bulk">
            <button
              class="cp-drop small"
              :class="{ dragover: dragKey === kind.key }"
              type="button"
              @click="inputs[`bulk:${kind.key}`]?.click()"
              @dragleave.prevent="dragKey = ''"
              @dragover.prevent="dragKey = kind.key"
              @drop.prevent="onBulkDrop(kind, $event)"
            >
              <cp-icon class="ic" :size="20" :width="1.5" name="upload" />
              <span class="big">{{ $t(`contribute.timeseries.kind.${kind.key}`) }}</span>
              <span class="small">{{ kind.directory }}</span>
            </button>
            <input
              :ref="(el) => (inputs[`bulk:${kind.key}`] = el as HTMLInputElement)"
              accept=".csv,text/csv"
              hidden
              multiple
              type="file"
              @change="onBulkSelect(kind, $event)"
            />
            <div
              v-if="bulkReport[kind.key]"
              class="cp-hint"
              :class="bulkReport[kind.key].unmatched.length ? 'err' : 'ok'"
            >
              <cp-icon :size="13" :name="bulkReport[kind.key].unmatched.length ? 'alert' : 'check'" />
              {{
                $t('contribute.timeseries.bulk_result', {
                  attached: bulkReport[kind.key].attached
                })
              }}
              <template v-if="bulkReport[kind.key].unmatched.length">
                {{
                  $t('contribute.timeseries.bulk_unmatched', {
                    files: bulkReport[kind.key].unmatched.slice(0, 5).join(', ')
                  })
                }}
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- Per experiment: one slot per kind. -->
      <div v-for="row in experiments" :key="row.uid" class="cp-fieldset">
        <div class="cp-fset-h">
          {{ row.id }}
          <span class="ct">{{ $t('contribute.timeseries.per_experiment') }}</span>
        </div>
        <div class="cp-fset-body">
          <div v-for="kind in kinds" :key="kind.key" class="cp-ts-slot">
            <div class="cp-ts-kind">{{ $t(`contribute.timeseries.kind.${kind.key}`) }}</div>
            <div v-if="store.timeSeries[`${row.uid}:${kind.key}`]" class="cp-file">
              <span class="fic">CSV</span>
              <div class="meta">
                <div class="fn">{{ store.timeSeries[`${row.uid}:${kind.key}`].name }}</div>
                <div class="fs">
                  {{
                    $t('contribute.timeseries.rows', {
                      count: store.timeSeries[`${row.uid}:${kind.key}`].rows
                    })
                  }}
                  → {{ row.id }}.csv
                </div>
              </div>
              <button
                class="fx"
                type="button"
                :aria-label="$t('contribute.timeseries.remove')"
                @click="remove(row.uid, kind)"
              >
                <cp-icon :size="13" name="close" />
              </button>
            </div>
            <template v-else>
              <button
                class="cp-btn ghost"
                type="button"
                @click="inputs[`${row.uid}:${kind.key}`]?.click()"
              >
                <cp-icon :size="14" name="upload" />{{ $t('contribute.timeseries.attach') }}
              </button>
              <input
                :ref="(el) => (inputs[`${row.uid}:${kind.key}`] = el as HTMLInputElement)"
                accept=".csv,text/csv"
                hidden
                type="file"
                @change="onSlotSelect(row.uid, kind, $event)"
              />
            </template>
            <div v-if="errors[`${row.uid}:${kind.key}`]" class="cp-hint err">
              <cp-icon :size="13" name="alert" />{{ errors[`${row.uid}:${kind.key}`] }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="idlessCount" class="cp-hint">
        <cp-icon :size="13" name="info" />
        {{ $t('contribute.timeseries.idless', { count: idlessCount }) }}
      </div>
    </template>
  </div>
</template>
