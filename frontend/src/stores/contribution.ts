import { defaultApi } from '@/plugins/axios'
import { buildCsv, CONTRIBUTION_DATABASES } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import { buildTarGz } from '@/utils/tar'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import type { ValidationResponse } from '@/utils/validationResponse'
import { isValidationResponse } from '@/utils/validationResponse'
import { isAxiosError } from 'axios'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type { ValidationResponse } from '@/utils/validationResponse'

export type QualityCheckStatus =
  | 'idle'
  | 'running'
  /** Validation ran and the record is clean. */
  | 'pass'
  /** Validation ran, no errors, but the validator raised warnings. */
  | 'warn'
  /** Validation ran and rejected the record. */
  | 'fail'
  /** The backend has no validator for this database. */
  | 'unsupported'
  /** The request itself failed — network, transport, or a server-side crash. */
  | 'error'

function deriveStatus(response: ValidationResponse): QualityCheckStatus {
  if (!response.valid) return 'fail'
  return response.results.some((file) => file.warnings.length > 0) ? 'warn' : 'pass'
}

/** Human-readable message for a failed `/validate` request (not a data error). */
function transportError(caught: unknown): string {
  if (isAxiosError(caught)) {
    const status = caught.response?.status
    if (status === 429) return 'Too many checks in a short time — wait a moment and retry.'
    if (status === 413) return 'The contribution is too large to validate in one request.'
    if (status === 400) return 'The generated archive could not be read by the server.'
    const detail = (caught.response?.data as { detail?: string } | undefined)?.detail
    if (detail) return detail
  }
  return caught instanceof Error ? caught.message : String(caught)
}

/** A measured-response file attached to the record, held in memory until upload. */
export interface AttachedTimeSeries {
  /** Name the file takes inside the archive, e.g. `DEMO-BRC-001.csv`. */
  name: string
  content: string
  rows: number
}

export const useContributionStore = defineStore('contribution', () => {
  const currentStep = ref(0)
  const database = ref<DatabaseId | null>(null)
  const program = ref('')
  const year = ref('')
  const doi = ref('')
  /** Metadata form values, keyed by table column. */
  const values = ref<Record<string, string>>({})
  /** Attached time-series, keyed by `TimeSeriesKind.key`. */
  const timeSeries = ref<Record<string, AttachedTimeSeries>>({})

  const status = ref<QualityCheckStatus>('idle')
  const response = ref<ValidationResponse | null>(null)
  const errorMessage = ref('')

  const specimenId = computed(() => values.value.id?.trim() ?? '')

  const config = computed(() => (database.value ? CONTRIBUTION_DATABASES[database.value] : null))

  const filledCount = computed(
    () => Object.values(values.value).filter((value) => (value ?? '').trim() !== '').length
  )

  function selectDatabase(id: DatabaseId): void {
    if (database.value === id) return
    // Columns differ per database, so carrying values across would leave
    // orphaned keys that never reach the CSV.
    database.value = id
    values.value = {}
    timeSeries.value = {}
    resetQualityCheck()
  }

  function resetQualityCheck(): void {
    status.value = 'idle'
    response.value = null
    errorMessage.value = ''
  }

  async function runQualityCheck(): Promise<void> {
    const target = config.value
    if (!target || !database.value) return

    if (!target.qualityCheckSupported) {
      status.value = 'unsupported'
      return
    }

    status.value = 'running'
    response.value = null
    errorMessage.value = ''

    try {
      // The primary CSV plus any attached time-series, each in the directory its
      // subsidiary type is globbed from. The validator resolves a time-series
      // file's foreign key from its filename against the primary CSV's `id`, so
      // both must travel in the same archive.
      const entries = [
        { path: target.csvPath, content: buildCsv(database.value, values.value) },
        ...timeSeriesKindsFor(database.value)
          .filter((kind) => timeSeries.value[kind.key])
          .map((kind) => ({
            path: `${kind.directory}/${timeSeries.value[kind.key].name}`,
            content: timeSeries.value[kind.key].content
          }))
      ]
      const archive = await buildTarGz(entries, 'contribution.tar.gz')
      const { data } = await defaultApi.validateData(target.type, archive)
      if (!isValidationResponse(data)) {
        throw new Error('Unexpected validation response shape.')
      }
      response.value = data
      status.value = deriveStatus(data)
    } catch (caught) {
      // The validator now returns 200 for data errors too, so a rejection here
      // means a transport problem: 400 (bad archive), 413 (too large), 429
      // (rate limited) or a 5xx. Surface a message the UI can show.
      status.value = 'error'
      errorMessage.value = transportError(caught)
    }
  }

  function reset(): void {
    currentStep.value = 0
    database.value = null
    program.value = ''
    year.value = ''
    doi.value = ''
    values.value = {}
    timeSeries.value = {}
    resetQualityCheck()
  }

  return {
    currentStep,
    database,
    program,
    year,
    doi,
    values,
    timeSeries,
    status,
    response,
    errorMessage,
    specimenId,
    config,
    filledCount,
    selectDatabase,
    resetQualityCheck,
    runQualityCheck,
    reset
  }
})
