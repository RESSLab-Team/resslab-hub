<script setup lang="ts">
import CpIcon from '@/components/contribute/CpIcon.vue'
import { useContributionStore } from '@/stores/contribution'
import { readCsvRecord, type CsvRecord } from '@/utils/csv'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const store = useContributionStore()

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
      throw new Error(t('contribute.files.import_no_match'))
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
  importFile((event.target as HTMLInputElement).files?.[0])
  // Clear so re-picking the same file fires change again.
  ;(event.target as HTMLInputElement).value = ''
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

    <template v-else>
      <div class="cp-fieldset">
        <div class="cp-fset-h">
          {{ $t('contribute.files.import') }}
          <span class="ct"
            >{{ store.config?.columns.length }} {{ $t('contribute.files.columns') }}</span
          >
        </div>
        <div class="cp-fset-body">
          <button
            class="cp-drop"
            :class="{ dragover: dragging }"
            type="button"
            @click="fileInput?.click()"
            @dragleave.prevent="dragging = false"
            @dragover.prevent="dragging = true"
            @drop.prevent="onDrop"
          >
            <cp-icon class="ic" :size="34" :width="1.5" name="upload" />
            <span class="big">
              <i18n-t keypath="contribute.files.drop_big" tag="span">
                <template #browse>
                  <b>{{ $t('contribute.files.browse') }}</b>
                </template>
              </i18n-t>
            </span>
            <span class="small">{{ $t('contribute.files.drop_small') }}</span>
          </button>
          <input ref="fileInput" accept=".csv,text/csv" hidden type="file" @change="onSelect" />

          <div v-if="error" class="cp-hint err" style="margin-top: 14px">
            <cp-icon :size="13" name="alert" />
            {{ $t('contribute.files.import_failed', { file: fileName }) }} {{ error }}
          </div>

          <template v-else-if="report">
            <div class="cp-hint ok" style="margin-top: 14px">
              <cp-icon :size="13" name="check" />
              {{
                $t('contribute.files.import_ok', {
                  file: fileName,
                  matched: report.matched.length,
                  filled: Object.keys(report.values).length
                })
              }}
            </div>
            <div v-if="report.rowCount > 1" class="cp-hint">
              {{ $t('contribute.files.import_first_row', { count: report.rowCount }) }}
            </div>
            <div v-if="report.unknown.length" class="cp-hint">
              {{
                $t('contribute.files.import_unknown', {
                  count: report.unknown.length,
                  columns: report.unknown.slice(0, 6).join(', ')
                })
              }}
            </div>
          </template>

          <div class="cp-metanote">
            <cp-icon :size="15" name="info" />
            <span>{{ $t('contribute.files.import_note') }}</span>
          </div>
        </div>
      </div>

      <div class="cp-fieldset">
        <div class="cp-fset-h">
          {{ $t('contribute.files.timeseries') }}
          <span class="ct">{{ $t('contribute.files.optional_stub') }}</span>
        </div>
        <div class="cp-fset-body">
          <div class="cp-drop is-disabled">
            <cp-icon class="ic" :size="34" :width="1.5" name="upload" />
            <div class="big">{{ $t('contribute.files.timeseries_soon') }}</div>
            <div class="small">{{ $t('contribute.files.timeseries_kinds') }}</div>
          </div>
          <div class="cp-metanote">
            <cp-icon :size="15" name="info" />
            <span>{{ $t('contribute.files.note') }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
