<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useContributionStore } from '@/stores/contribution'
import { fieldLabel } from '@/utils/contribution'
import { readCsvRecord, type CsvRecord } from '@/utils/csv'
import { DATABASES } from '@/utils/navigation'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()

const databaseName = computed(
  () => DATABASES.find((entry) => entry.id === store.database)?.name ?? ''
)
const columns = computed(() => store.config?.columns ?? [])

const fileInput = ref<HTMLInputElement>()
const dragging = ref(false)
const fileName = ref('')
const report = ref<CsvRecord | null>(null)
const error = ref('')

async function importFile(file: File | undefined): Promise<void> {
  if (!file || !store.config || !store.database) return

  fileName.value = file.name
  report.value = null
  error.value = ''

  try {
    const record = readCsvRecord(await file.text(), store.config.columns)
    if (record.matched.length === 0) {
      throw new Error(t('contribute.metadata.import_no_match'))
    }
    // Replace rather than merge: a half-overwritten record mixing two sources
    // is harder to reason about than a clean import.
    store.values = { ...record.values }
    store.resetQualityCheck()
    report.value = record
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : String(caught)
  }
}

function onDrop(event: DragEvent): void {
  dragging.value = false
  importFile(event.dataTransfer?.files[0])
}

function onSelect(event: Event): void {
  const input = event.target as HTMLInputElement
  importFile(input.files?.[0])
  // Clear so re-picking the same file fires change again.
  input.value = ''
}

function clearAll(): void {
  store.values = {}
  store.resetQualityCheck()
  report.value = null
  error.value = ''
  fileName.value = ''
}
</script>

<template>
  <div>
    <div class="cp-wsectionlabel">
      {{ $t('contribute.wizard.step_label', { current: 2, total: 5 }) }}
      <template v-if="databaseName"> · {{ databaseName.toUpperCase() }}</template>
    </div>
    <h2 class="cp-wh">{{ $t('contribute.metadata.title') }}</h2>
    <p class="cp-wsub">{{ $t('contribute.metadata.subtitle') }}</p>

    <p v-if="!store.database" class="cp-hint">
      {{ $t('contribute.metadata.select_database_first') }}
    </p>

    <template v-else>
      <div class="cp-metasum">
        <cp-icon :size="15" name="layers" />
        <b>{{ $t('contribute.metadata.summary_fields', { count: columns.length }) }}</b>
        <span>·</span>
        <span class="mut">{{ $t('contribute.metadata.summary_blank') }}</span>
      </div>

      <!-- Optional shortcut: fill every field from a prepared record. Hand entry
           below stays the primary path. -->
      <div class="cp-prefill" :class="{ dragover: dragging }">
        <button
          class="cp-prefill-zone"
          type="button"
          @click="fileInput?.click()"
          @dragleave.prevent="dragging = false"
          @dragover.prevent="dragging = true"
          @drop.prevent="onDrop"
        >
          <cp-icon :size="18" :width="1.6" name="upload" />
          <span class="txt">
            <i18n-t keypath="contribute.metadata.import_prompt" tag="span">
              <template #browse>
                <b>{{ $t('contribute.metadata.import_browse') }}</b>
              </template>
            </i18n-t>
            <span class="sub">{{ $t('contribute.metadata.import_hint') }}</span>
          </span>
        </button>
        <button
          v-if="store.filledCount > 0"
          class="cp-prefill-clear"
          type="button"
          @click="clearAll"
        >
          {{ $t('contribute.metadata.import_clear') }}
        </button>
      </div>
      <input ref="fileInput" accept=".csv,text/csv" hidden type="file" @change="onSelect" />

      <div v-if="error" class="cp-hint err">
        <cp-icon :size="13" name="alert" />
        {{ $t('contribute.metadata.import_failed', { file: fileName }) }} {{ error }}
      </div>
      <template v-else-if="report">
        <div class="cp-hint ok">
          <cp-icon :size="13" name="check" />
          {{
            $t('contribute.metadata.import_ok', {
              file: fileName,
              matched: report.matched.length,
              filled: Object.keys(report.values).length
            })
          }}
        </div>
        <div v-if="report.rowCount > 1" class="cp-hint">
          {{ $t('contribute.metadata.import_first_row', { count: report.rowCount }) }}
        </div>
        <div v-if="report.unknown.length" class="cp-hint">
          {{
            $t('contribute.metadata.import_unknown', {
              count: report.unknown.length,
              columns: report.unknown.slice(0, 6).join(', ')
            })
          }}
        </div>
      </template>

      <div class="cp-fieldset" style="margin-top: 22px">
        <div class="cp-fset-h">
          {{ $t('contribute.metadata.fields') }}
          <span class="ct">{{ store.filledCount }} / {{ columns.length }}</span>
        </div>
        <div class="cp-fset-body">
          <div class="cp-grid2">
            <div v-for="column in columns" :key="column" class="cp-field">
              <label class="cp-label" :for="`cp-f-${column}`">
                {{ fieldLabel(store.database, column) }}
                <span v-if="column === 'id'" class="req">*</span>
              </label>
              <input
                :id="`cp-f-${column}`"
                v-model="store.values[column]"
                class="cp-input"
                type="text"
              />
            </div>
          </div>

          <div class="cp-metanote">
            <cp-icon :size="15" name="info" />
            <span>{{ $t('contribute.metadata.id_required') }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
