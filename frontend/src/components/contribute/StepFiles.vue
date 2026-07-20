<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useContributionStore } from '@/stores/contribution'
import { parseCsv } from '@/utils/csv'
import { timeSeriesKindsFor, type TimeSeriesKind } from '@/utils/timeseries'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()

const kinds = computed(() => timeSeriesKindsFor(store.database))
const inputs = ref<Record<string, HTMLInputElement | null>>({})
const draggingKey = ref('')
const errors = ref<Record<string, string>>({})

/** The validator reads the foreign key from the filename, not from a column. */
function expectedName(): string {
  return store.specimenId ? `${store.specimenId}.csv` : ''
}

async function attach(kind: TimeSeriesKind, file: File | undefined): Promise<void> {
  if (!file) return
  delete errors.value[kind.key]

  try {
    const rows = parseCsv(await file.text())
    if (rows.length < 2) {
      throw new Error(t('contribute.timeseries.error_empty'))
    }
    const headers = rows[0].map((header) => header.trim())
    const missing = kind.requiredColumns.filter((column) => !headers.includes(column))
    if (missing.length) {
      throw new Error(
        t('contribute.timeseries.error_columns', { columns: missing.join(', ') })
      )
    }

    // Rename to the specimen id: the file's own name would otherwise become the
    // foreign key and fail against the record being submitted alongside it.
    store.timeSeries[kind.key] = {
      name: expectedName() || file.name,
      content: await file.text(),
      rows: rows.length - 1
    }
    store.resetQualityCheck()
  } catch (caught) {
    errors.value[kind.key] = caught instanceof Error ? caught.message : String(caught)
  }
}

function remove(kind: TimeSeriesKind): void {
  delete store.timeSeries[kind.key]
  delete errors.value[kind.key]
  store.resetQualityCheck()
}

function onDrop(kind: TimeSeriesKind, event: DragEvent): void {
  draggingKey.value = ''
  attach(kind, event.dataTransfer?.files[0])
}

function onSelect(kind: TimeSeriesKind, event: Event): void {
  const input = event.target as HTMLInputElement
  attach(kind, input.files?.[0])
  input.value = ''
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

    <template v-else>
      <div class="cp-metasum">
        <cp-icon :size="15" name="layers" />
        <b>{{ $t('contribute.timeseries.summary', { count: kinds.length }) }}</b>
        <span>·</span>
        <span class="mut">{{ $t('contribute.timeseries.optional') }}</span>
      </div>

      <div v-if="!store.specimenId" class="cp-eduflag" style="border-left-color: var(--epfl-orange)">
        <cp-icon :size="15" name="alert" />
        <span>{{ $t('contribute.timeseries.needs_id') }}</span>
      </div>

      <div v-for="kind in kinds" :key="kind.key" class="cp-fieldset">
        <div class="cp-fset-h">
          {{ $t(`contribute.timeseries.kind.${kind.key}`) }}
          <span class="ct">{{ kind.directory }}</span>
        </div>
        <div class="cp-fset-body">
          <div v-if="store.timeSeries[kind.key]" class="cp-file">
            <span class="fic">CSV</span>
            <div class="meta">
              <div class="fn">{{ store.timeSeries[kind.key].name }}</div>
              <div class="fs">
                {{
                  $t('contribute.timeseries.rows', { count: store.timeSeries[kind.key].rows })
                }}
              </div>
            </div>
            <div class="fstate">
              <span class="cp-hint ok" style="margin: 0">
                <cp-icon :size="13" name="check" />{{ $t('contribute.timeseries.attached') }}
              </span>
              <button
                class="fx"
                type="button"
                :aria-label="$t('contribute.timeseries.remove')"
                @click="remove(kind)"
              >
                <cp-icon :size="13" name="close" />
              </button>
            </div>
          </div>

          <button
            v-else
            class="cp-drop"
            :class="{ dragover: draggingKey === kind.key }"
            type="button"
            @click="inputs[kind.key]?.click()"
            @dragleave.prevent="draggingKey = ''"
            @dragover.prevent="draggingKey = kind.key"
            @drop.prevent="onDrop(kind, $event)"
          >
            <cp-icon class="ic" :size="30" :width="1.5" name="upload" />
            <span class="big">
              <i18n-t keypath="contribute.timeseries.drop" tag="span">
                <template #browse>
                  <b>{{ $t('contribute.metadata.import_browse') }}</b>
                </template>
              </i18n-t>
            </span>
            <span class="small">{{ kind.requiredColumns.join(' · ') }}</span>
          </button>
          <input
            :ref="(el) => (inputs[kind.key] = el as HTMLInputElement)"
            accept=".csv,text/csv"
            hidden
            type="file"
            @change="onSelect(kind, $event)"
          />

          <div v-if="errors[kind.key]" class="cp-hint err">
            <cp-icon :size="13" name="alert" />
            {{ errors[kind.key] }}
          </div>
        </div>
      </div>

      <div class="cp-eduflag">
        <cp-icon :size="15" name="info" />
        <span>{{ $t('contribute.timeseries.rename_note', { name: expectedName() || '<id>.csv' }) }}</span>
      </div>
    </template>
  </div>
</template>
