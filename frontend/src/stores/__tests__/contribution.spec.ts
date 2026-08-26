import { NO_TEST_DATA_MESSAGE, useContributionStore } from '@/stores/contribution'
import { useDictionaryStore, type DictColumn } from '@/stores/dictionary'
import { buildCsv } from '@/utils/contribution'
import { postContribution } from '@/utils/submission'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import { nextTick } from 'vue'

vi.mock('@/utils/submission', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/utils/submission')>()),
  postContribution: vi.fn()
}))

// jsdom has no CompressionStream; the archive itself is covered by tar tests.
vi.mock('@/utils/tar', () => ({
  buildTarGz: vi.fn(async () => new File(['tar'], 'contribution.tar.gz'))
}))

const BRACE_COLUMNS: DictColumn[] = [
  {
    name: 'id',
    description: '',
    symbol: '',
    unit: '-',
    type: 'String',
    example: 'B1',
    nullable: false
  },
  {
    name: 'area',
    description: '',
    symbol: '',
    unit: 'mm2',
    type: 'Numeric',
    example: '10',
    nullable: true
  },
  {
    name: 'investigator',
    description: '',
    symbol: '',
    unit: '-',
    type: 'String',
    example: 'X',
    nullable: false
  }
]

function seededStore(columns: DictColumn[] = BRACE_COLUMNS) {
  const dictionary = useDictionaryStore()
  dictionary.columns = { braces: columns }
  dictionary.state = 'ready'
  const store = useContributionStore()
  store.selectDatabase('braces')
  return store
}

/** Braces expect a force-displacement file; give the row one named after its id. */
function attachTestData(store: ReturnType<typeof seededStore>, uid: number, name?: string) {
  const id = (store.rowByUid(uid)?.cells.id ?? '').trim()
  store.timeSeries[`${uid}:force_displacement`] = {
    name: name ?? `${id}.csv`,
    content: 'Displacement [mm],Force [kN]\n0,0\n',
    rows: 1
  }
}

describe('buildCsv (multi-row)', () => {
  it('writes the header in column order and one row per experiment', () => {
    const names = BRACE_COLUMNS.map((column) => column.name)
    const csv = buildCsv(names, [{ id: 'B1', area: '10' }, { id: 'B2' }])
    const lines = csv.trimEnd().split('\n')
    expect(lines[0]).toBe('id,area,investigator')
    expect(lines.length - 1).toBe(2)
    expect(lines[1]).toBe('B1,10,NR') // blanks become NR
    expect(lines[2]).toBe('B2,NR,NR')
  })
})

describe('contribution store — experiment rows', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('starts with one row and resets rows on database change', () => {
    const store = seededStore()
    store.rows[0].cells.id = 'B1'
    store.selectDatabase('columns')
    expect(store.rows.length).toBe(1)
    expect(store.rows[0].cells.id).toBeUndefined()
  })

  it('adds, duplicates (clearing id) and removes rows', () => {
    const store = seededStore()
    store.rows[0].cells.id = 'B1'
    store.rows[0].cells.area = '10'
    store.addRow()
    expect(store.rows.length).toBe(2)

    store.duplicateRow(store.rows[0].uid)
    const copy = store.rows[2]
    expect(copy.cells.area).toBe('10')
    expect(copy.cells.id).toBe('')

    const keep = store.rows[1].uid
    store.removeRow(store.rows[0].uid)
    expect(store.rows.some((row) => row.uid === keep)).toBe(true)
    expect(store.rows.length).toBe(2)
  })

  it('always keeps at least one row', () => {
    const store = seededStore()
    store.removeRow(store.rows[0].uid)
    expect(store.rows.length).toBe(1)
  })

  it('drops a row’s attached time-series when it is removed', () => {
    const store = seededStore()
    const uid = store.rows[0].uid
    store.timeSeries[`${uid}:force_displacement`] = { name: 'x.csv', content: 'a\n1', rows: 1 }
    store.addRow()
    store.removeRow(uid)
    expect(store.timeSeries[`${uid}:force_displacement`]).toBeUndefined()
  })

  it('dismisses a warning, and brings it back when the value changes', () => {
    const store = seededStore()
    const row = store.rows[0]
    row.cells.id = 'B1'
    attachTestData(store, row.uid)
    row.cells.area = '1.5' // Numeric is fine, but "investigator" is blank -> warning

    const warning = store.activeIssuesFor(row.uid).find((issue) => issue.level === 'warn')
    expect(warning?.column).toBe('investigator')
    expect(store.levelFor(row.uid)).toBe('warn')

    store.dismissIssue(warning!.key)
    expect(store.activeIssuesFor(row.uid)).toHaveLength(0)
    expect(store.dismissedIssuesFor(row.uid)).toHaveLength(1)
    expect(store.dismissedCount).toBe(1)
    expect(store.levelFor(row.uid)).toBe('pass')
    // The field stops showing it inline too.
    expect(store.cellIssueFor(row.uid, 'investigator')).toBeUndefined()

    // A dismissal follows the value that was acknowledged, so filling the field
    // clears the warning outright and blanking it again stays acknowledged.
    row.cells.investigator = 'Someone'
    expect(store.activeIssuesFor(row.uid)).toHaveLength(0)
    expect(store.dismissedIssuesFor(row.uid)).toHaveLength(0)
    row.cells.investigator = ''
    expect(store.dismissedIssuesFor(row.uid)).toHaveLength(1)
  })

  it('re-raises a dismissed warning when the value it was about changes', () => {
    const store = seededStore([
      ...BRACE_COLUMNS,
      {
        name: 'cycles',
        description: '',
        symbol: '',
        unit: '-',
        type: 'Integer',
        example: '2',
        nullable: true
      }
    ])
    const row = store.rows[0]
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
    attachTestData(store, row.uid)
    row.cells.cycles = '1.5' // warns: will be truncated

    const warning = store.activeIssuesFor(row.uid).find((issue) => issue.column === 'cycles')
    store.dismissIssue(warning!.key)
    expect(store.activeIssuesFor(row.uid)).toHaveLength(0)

    row.cells.cycles = '2.5' // same warning, different value -> ask again
    expect(store.activeIssuesFor(row.uid)).toHaveLength(1)
    expect(store.dismissedIssuesFor(row.uid)).toHaveLength(0)
  })

  it('never dismisses an error', () => {
    const store = seededStore()
    const row = store.rows[0]
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
    attachTestData(store, row.uid)
    row.cells.area = 'not-a-number'

    const error = store.activeIssuesFor(row.uid).find((issue) => issue.level === 'error')
    store.dismissIssue(error!.key)
    expect(store.activeIssuesFor(row.uid)).toHaveLength(1)
    expect(store.levelFor(row.uid)).toBe('fail')
  })

  it('restores dismissals per experiment and clears them on database change', () => {
    const store = seededStore()
    store.importRows([{ id: 'B1' }, { id: 'B2' }])
    const [first, second] = store.rows
    for (const row of store.rows) attachTestData(store, row.uid)
    for (const row of store.rows) {
      for (const issue of store.activeIssuesFor(row.uid)) store.dismissIssue(issue.key)
    }
    expect(store.dismissedCount).toBe(2)

    store.restoreDismissed(first.uid)
    expect(store.dismissedIssuesFor(first.uid)).toHaveLength(0)
    expect(store.dismissedIssuesFor(second.uid)).toHaveLength(1)

    store.restoreDismissed()
    expect(store.dismissedCount).toBe(0)

    for (const issue of store.activeIssuesFor(second.uid)) store.dismissIssue(issue.key)
    store.selectDatabase('columns')
    expect(store.dismissedCount).toBe(0)
  })

  it('reports a pending verdict until the server has judged the batch', () => {
    const store = seededStore()
    // Nothing to check yet: no identifier, so no request will be made.
    expect(store.checking).toBe(false)

    store.rows[0].cells.id = 'B1'
    expect(store.checking).toBe(true) // queued behind the debounce
    store.status = 'running'
    expect(store.checking).toBe(true)

    store.status = 'pass'
    expect(store.checking).toBe(false)
    expect(store.unverified).toBe(false)

    store.status = 'error'
    expect(store.checking).toBe(false)
    expect(store.unverified).toBe(true)
  })

  it('says up front that a database without a validator cannot be checked', async () => {
    const dictionary = useDictionaryStore()
    dictionary.columns = { braces: BRACE_COLUMNS, ebf: BRACE_COLUMNS }
    dictionary.state = 'ready'
    const store = useContributionStore()
    store.selectDatabase('ebf')
    expect(store.status).toBe('unsupported')
    store.rows[0].cells.id = 'E1'
    await nextTick()
    expect(store.status).toBe('unsupported')
    expect(store.checking).toBe(false)
    store.selectDatabase('braces')
    expect(store.status).toBe('idle')
  })

  it('warns when an experiment has no test data, until a file is attached', () => {
    const store = seededStore()
    const row = store.rows[0]
    // No id yet: the missing id is the problem, not the missing file.
    expect(store.activeIssuesFor(row.uid).some((i) => i.message === NO_TEST_DATA_MESSAGE)).toBe(
      false
    )
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
    const warning = store.activeIssuesFor(row.uid).find((issue) => issue.kindKey === null)
    expect(warning?.level).toBe('warn')
    expect(warning?.message).toBe(NO_TEST_DATA_MESSAGE)
    expect(store.withoutTestDataCount).toBe(1)
    store.dismissIssue(warning!.key)
    expect(store.dismissedWarningMessages).toEqual([`B1: ${NO_TEST_DATA_MESSAGE}`])
    attachTestData(store, row.uid)
    expect(store.activeIssuesFor(row.uid)).toHaveLength(0)
    expect(store.dismissedIssuesFor(row.uid)).toHaveLength(0)
    expect(store.withoutTestDataCount).toBe(0)
  })

  it('warns when an attached file is not named after the specimen id', () => {
    const store = seededStore()
    const row = store.rows[0]
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
    attachTestData(store, row.uid, 'run_07_raw.csv')
    const warning = store
      .activeIssuesFor(row.uid)
      .find((issue) => issue.kindKey === 'force_displacement')
    expect(warning?.level).toBe('warn')
    expect(warning?.message).toContain('run_07_raw.csv')
    // Any capitalisation of the extension is fine; only the stem matters.
    attachTestData(store, row.uid, 'B1.CSV')
    expect(store.activeIssuesFor(row.uid)).toHaveLength(0)
  })

  it('summarises unresolved problems per experiment, in batch order', () => {
    const store = seededStore()
    store.importRows([{ id: 'B1', investigator: 'X' }, { id: 'B2', area: 'abc' }, { id: '' }])
    const [first, second, third] = store.rows
    attachTestData(store, first.uid)
    const counts = store.problemSummary.map(({ issues, ...entry }) => ({
      ...entry,
      issues: issues.length
    }))
    expect(counts).toEqual([
      { uid: second.uid, index: 1, id: 'B2', errors: 1, warnings: 2, issues: 3 },
      { uid: third.uid, index: 2, id: '', errors: 1, warnings: 1, issues: 2 } // blank investigator warns
    ])
    expect(store.activeErrorCount).toBe(2)
    for (const issue of store.activeIssuesFor(second.uid)) store.dismissIssue(issue.key)
    const [remaining] = store.problemSummary
    expect([remaining.errors, remaining.warnings]).toEqual([1, 0])
    // A lone problem travels with the summary, so the bar can show it in place.
    expect(remaining.issues.map((issue) => issue.column)).toEqual(['area'])
  })

  it('imports rows and counts client-side errors', () => {
    const store = seededStore()
    store.importRows([
      { id: 'B1', area: 'not-a-number' },
      { id: '' } // missing id -> error
    ])
    expect(store.rows.length).toBe(2)
    expect(store.experimentCount).toBe(2)
    expect(store.specimenIds).toEqual(['B1'])
    expect(store.clientErrorCount).toBeGreaterThanOrEqual(2)
  })
})

describe('contribution store — submission', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(postContribution).mockReset()
  })

  const CONTRIBUTOR = { name: 'Ada', email: 'ada@example.edu', institution: '', orcid: '' }

  /** Edits flush the reset watcher; settle it before handing out a verdict. */
  async function submittableStore() {
    const store = seededStore()
    const row = store.rows[0]
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
    await nextTick()
    store.status = 'pass'
    return store
  }

  it('gates canSubmit on a clean batch with a server verdict', async () => {
    const store = seededStore()
    expect(store.canSubmit).toBe(false) // no id, no verdict

    const row = store.rows[0]
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
    await nextTick()
    store.status = 'pass'
    expect(store.canSubmit).toBe(true)

    store.status = 'warn'
    expect(store.canSubmit).toBe(true) // warnings never block

    store.status = 'fail'
    expect(store.canSubmit).toBe(false)
    store.status = 'unsupported'
    expect(store.canSubmit).toBe(false) // no server validator -> no PR
  })

  it('submits the batch and records the pull request', async () => {
    const store = await submittableStore()
    vi.mocked(postContribution).mockResolvedValue({
      pr_url: 'https://github.com/x/pull/7',
      pr_number: 7,
      branch: 'contrib/braces/b1-abc'
    })

    await store.submit(CONTRIBUTOR)

    expect(store.submitStatus).toBe('submitted')
    expect(store.pullRequestUrl).toBe('https://github.com/x/pull/7')
    expect(store.pullRequestNumber).toBe(7)
    const [, archive, contributor] = (postContribution as Mock).mock.calls[0]
    expect(archive).toBeInstanceOf(File)
    expect(contributor).toEqual(CONTRIBUTOR)
  })

  it('passes dismissed warnings, labelled by specimen id', async () => {
    const store = seededStore()
    const row = store.rows[0]
    row.cells.id = 'B1' // "investigator" left blank -> warning
    const warning = store.activeIssuesFor(row.uid).find((issue) => issue.level === 'warn')
    store.dismissIssue(warning!.key)
    await nextTick()
    store.status = 'warn'
    vi.mocked(postContribution).mockResolvedValue({
      pr_url: 'u',
      pr_number: 1,
      branch: 'b'
    })

    await store.submit(CONTRIBUTOR)

    const [, , , dismissed] = (postContribution as Mock).mock.calls[0]
    expect(dismissed).toHaveLength(1)
    expect(dismissed[0]).toMatch(/^B1: /)
  })

  it('shows the server’s own reason when a submission is refused', async () => {
    const store = await submittableStore()
    vi.mocked(postContribution).mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 400,
        data: { detail: "Specimen id 'a/b' cannot be used as a file name: rule." }
      }
    })

    await store.submit(CONTRIBUTOR)

    expect(store.submitStatus).toBe('error')
    expect(store.submitError).toBe("Specimen id 'a/b' cannot be used as a file name: rule.")
  })

  it('falls back to the archive message only when a 400 carries no detail', async () => {
    const store = await submittableStore()
    vi.mocked(postContribution).mockRejectedValue({
      isAxiosError: true,
      response: { status: 400, data: '<html>bad request</html>' }
    })

    await store.submit(CONTRIBUTOR)

    expect(store.submitError).toContain('could not be read')
  })

  it('maps a 422 validation report onto the editor and reports the failure', async () => {
    const store = await submittableStore()
    vi.mocked(postContribution).mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 422,
        data: {
          valid: false,
          message: 'Validation failed',
          error_count: 1,
          results: [
            {
              file: 'steel_braces.csv',
              path: 'braces/steel_braces.csv',
              valid: false,
              errors: [{ row: 1, column: 'id', value: 'B1', message: 'already exists' }],
              warnings: []
            }
          ],
          error_results: [],
          valid_results: []
        }
      }
    })

    await store.submit(CONTRIBUTOR)

    expect(store.submitStatus).toBe('error')
    expect(store.status).toBe('fail')
    expect(store.response?.error_count).toBe(1)
  })

  it('does nothing when the batch is not submittable', async () => {
    const store = seededStore()
    await store.submit(CONTRIBUTOR)
    expect(postContribution).not.toHaveBeenCalled()
    expect(store.submitStatus).toBe('idle')
  })
})
