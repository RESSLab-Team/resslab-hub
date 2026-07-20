import { defaultApi } from '@/plugins/axios'
import { buildCsv, CONTRIBUTION_DATABASES } from '@/utils/contribution'
import type { DatabaseId } from '@/utils/navigation'
import { buildTarGz } from '@/utils/tar'
import { isAxiosError } from 'axios'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

/** One entry per validated file, as assembled by the backend's `/validate` route. */
export interface ValidationFileResult {
  file: string
  valid: boolean
  errors_count?: number
  errors?: string[]
  warnings?: string[]
}

export interface ValidationResponse {
  valid: boolean
  message: string
  error_count: number
  error_results: ValidationFileResult[]
  valid_results: ValidationFileResult[]
}

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
  /** The request itself failed — network, auth, or a server-side crash. */
  | 'error'

function isValidationResponse(data: unknown): data is ValidationResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'valid' in data &&
    'error_results' in data &&
    'valid_results' in data
  )
}

export const useContributionStore = defineStore('contribution', () => {
  const currentStep = ref(0)
  const database = ref<DatabaseId | null>(null)
  const program = ref('')
  const year = ref('')
  const doi = ref('')
  /** Metadata form values, keyed by table column. */
  const values = ref<Record<string, string>>({})

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
      const archive = await buildTarGz(
        [{ path: target.csvPath, content: buildCsv(database.value, values.value) }],
        'contribution.tar.gz'
      )
      const { data } = await defaultApi.validateData(target.type, archive)
      response.value = data as ValidationResponse
      status.value = response.value.valid_results.some((r) => r.warnings?.length) ? 'warn' : 'pass'
    } catch (caught) {
      // A rejected record comes back as a 422 carrying the same body as a pass.
      const data = isAxiosError(caught) ? caught.response?.data : undefined
      if (isValidationResponse(data)) {
        response.value = data
        status.value = 'fail'
        return
      }
      status.value = 'error'
      errorMessage.value = caught instanceof Error ? caught.message : String(caught)
    }
  }

  function reset(): void {
    currentStep.value = 0
    database.value = null
    program.value = ''
    year.value = ''
    doi.value = ''
    values.value = {}
    resetQualityCheck()
  }

  return {
    currentStep,
    database,
    program,
    year,
    doi,
    values,
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
