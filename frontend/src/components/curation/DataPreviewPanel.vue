<script setup lang="ts">
import type { CurationFile } from '@/backend'
import UnitLineChart from '@/components/commons/charts/UnitLineChart.vue'
import { useCurationStore } from '@/stores/curation'
import { kindForFile } from '@/utils/curation'
import { parseCsv } from '@/utils/csv'
import type { DatabaseId } from '@/utils/navigation'
import { mdiAlertOutline } from '@mdi/js'
import type { LineSeriesOption } from 'echarts'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * Line-chart previews of the time-series files attached to one experiment,
 * fetched from the submission's PR branch through the backend proxy.
 */
const props = defineProps<{
  database: DatabaseId
  prNumber: number
  files: CurationFile[]
}>()

const { t, te } = useI18n({ useScope: 'global' })
const store = useCurationStore()

interface Preview {
  path: string
  title: string
  xAxisName: string
  yAxisName: string
  rows: number
  series: LineSeriesOption[]
}

const previews = ref<Preview[]>([])
const failed = ref<string[]>([])
const loading = ref(false)

function kindLabel(key: string | undefined): string {
  const i18nKey = `contribute.timeseries.kind.${key}`
  return key && te(i18nKey) ? t(i18nKey) : key ?? ''
}

function buildPreview(file: CurationFile, text: string): Preview | null {
  const parsed = parseCsv(text)
  if (parsed.length < 2) return null
  const headers = parsed[0].map((header) => header.trim())
  const kind = kindForFile(props.database, file)
  // Prefer the kind's declared columns; fall back to the first two.
  const wanted = kind?.requiredColumns.length ? kind.requiredColumns : headers.slice(0, 2)
  const xIndex = Math.max(headers.indexOf(wanted[0]), 0)
  const yIndex = wanted.length > 1 ? Math.max(headers.indexOf(wanted[1]), 1) : 1
  const data: number[][] = []
  for (const row of parsed.slice(1)) {
    const x = Number(row[xIndex])
    const y = Number(row[yIndex])
    if (!Number.isNaN(x) && !Number.isNaN(y)) data.push([x, y])
  }
  if (!data.length) return null
  return {
    path: file.path,
    title: kindLabel(kind?.key),
    xAxisName: headers[xIndex] ?? '',
    yAxisName: headers[yIndex] ?? '',
    rows: parsed.length - 1,
    series: [{ data, showSymbol: false }]
  }
}

watch(
  () => [props.prNumber, props.files] as const,
  async ([prNumber, files]) => {
    loading.value = true
    previews.value = []
    failed.value = []
    const next: Preview[] = []
    const errors: string[] = []
    await Promise.all(
      files.map(async (file) => {
        try {
          const text = await store.fetchFileText(prNumber, file.path)
          const preview = buildPreview(file, text)
          if (preview) next.push(preview)
          else errors.push(file.path)
        } catch {
          errors.push(file.path)
        }
      })
    )
    next.sort((a, b) => a.path.localeCompare(b.path))
    previews.value = next
    failed.value = errors
    loading.value = false
  },
  { immediate: true }
)

const fileName = (path: string) => path.slice(path.lastIndexOf('/') + 1)
const empty = computed(() => !loading.value && !previews.value.length && !failed.value.length)
</script>

<template>
  <div class="tool-card">
    <div class="tool-card-h">{{ $t('curation.preview.title') }}</div>

    <p v-if="loading" class="state">{{ $t('curation.preview.loading') }}</p>
    <p v-else-if="empty" class="state">{{ $t('curation.preview.none') }}</p>

    <div v-for="preview in previews" :key="preview.path" class="preview">
      <div class="preview-head">
        <span class="preview-title">{{ preview.title }}</span>
        <span class="preview-meta">
          {{
            $t('curation.preview.rows_file', { rows: preview.rows, file: fileName(preview.path) })
          }}
        </span>
      </div>
      <unit-line-chart
        :series="preview.series"
        :x-axis-name="preview.xAxisName"
        :y-axis-name="preview.yAxisName"
        :aspect-ratio="2"
      />
    </div>

    <p v-for="path in failed" :key="path" class="state error">
      <v-icon :icon="mdiAlertOutline" size="14" />
      {{ $t('curation.preview.unavailable', { file: fileName(path) }) }}
    </p>
  </div>
</template>

<style scoped>
.state {
  margin: 4px 0;
  font-size: 13.5px;
  color: var(--fg-muted);
}
.state.error {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--epfl-orange);
}
.preview + .preview {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}
.preview-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}
.preview-title {
  font-size: 13px;
  font-weight: 600;
}
.preview-meta {
  font-size: 12px;
  color: var(--fg-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
</style>
