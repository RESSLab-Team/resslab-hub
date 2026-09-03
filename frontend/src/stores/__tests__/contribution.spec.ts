import { defaultApi } from '@/plugins/axios'
import {
  DRAFT_SETTLE_MS,
  MISSING_REQUIRED_MESSAGE,
  NO_TEST_DATA_MESSAGE,
  useContributionStore
} from '@/stores/contribution'
import { useDictionaryStore, type DictColumn } from '@/stores/dictionary'
import { buildCsv, CONTRIBUTION_DATABASES } from '@/utils/contribution'
import type { IntakePlan } from '@/utils/intake'
import type { DatabaseId } from '@/utils/navigation'
import { postContribution } from '@/utils/submission'
import { buildTarGz } from '@/utils/tar'
import { timeSeriesKindsFor } from '@/utils/timeseries'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest'
import { nextTick } from 'vue'

vi.mock('@/utils/submission', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/utils/submission')>()),
  postContribution: vi.fn()
}))

// jsdom has no CompressionStream; the archive itself is covered by tar tests.
vi.mock('@/utils/tar', () => ({
  buildTarGz: vi.fn(async () => new File(['tar'], 'contribution.tar.gz'))
}))

// The automatic check's request: answered clean, counted by the draft tests.
vi.mock('@/plugins/axios', () => ({
  defaultApi: { validateData: vi.fn(async () => ({ data: { valid: true, results: [] } })) }
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

function seededStore(columns: DictColumn[] = BRACE_COLUMNS, { draft = false } = {}) {
  const dictionary = useDictionaryStore()
  dictionary.columns = { braces: columns }
  dictionary.state = 'ready'
  const store = useContributionStore()
  store.selectDatabase('braces')
  // Most tests edit "the" row; the batch itself starts empty. A hand-added
  // row is a draft with its blank fields muted, so settle it unless a test is
  // about drafting itself.
  store.addRow()
  if (!draft) store.settle()
  return store
}

const FORCE_DISPLACEMENT = timeSeriesKindsFor('braces')[0]

/** Braces expect a force-displacement file; give the row one named after its id. */
function attachTestData(
  store: ReturnType<typeof seededStore>,
  uid: number,
  name?: string,
  content = 'Displacement [mm],Force [kN]\n0,0\n1,10\n'
) {
  const id = (store.rowByUid(uid)?.cells.id ?? '').trim()
  store.attachSeries(uid, FORCE_DISPLACEMENT, name ?? `${id}.csv`, content)
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

  it('starts empty and clears the batch on database change', () => {
    const dictionary = useDictionaryStore()
    dictionary.columns = { braces: BRACE_COLUMNS }
    dictionary.state = 'ready'
    const store = useContributionStore()
    expect(store.rows).toEqual([])
    store.selectDatabase('braces')
    expect(store.rows).toEqual([])
    const uid = store.addRow()
    store.rows[0].cells.id = 'B1'
    expect(store.rows[0].uid).toBe(uid)
    store.selectDatabase('columns')
    expect(store.rows).toEqual([])
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

  it('lets the last row go, back to the empty batch', () => {
    const store = seededStore()
    store.removeRow(store.rows[0].uid)
    expect(store.rows).toEqual([])
    store.importRows([])
    expect(store.rows).toEqual([])
  })

  it('drops a row’s attached time-series when it is removed', () => {
    const store = seededStore()
    const uid = store.rows[0].uid
    attachTestData(store, uid, 'x.csv')
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

  it('checks every database, EBF and ductile fracture included', async () => {
    // They used to answer 'unsupported': the backend had no validator for
    // them and the request came back as a 500 (resslab-hub#243).
    const dictionary = useDictionaryStore()
    dictionary.columns = {
      braces: BRACE_COLUMNS,
      ebf: BRACE_COLUMNS,
      'ductile-fracture': BRACE_COLUMNS
    }
    dictionary.state = 'ready'
    const store = useContributionStore()
    for (const database of ['ebf', 'ductile-fracture', 'braces'] as DatabaseId[]) {
      store.selectDatabase(database)
      expect(store.status).toBe('idle')
      expect(store.checking).toBe(false)
    }
    expect(
      Object.values(CONTRIBUTION_DATABASES).every((entry) => entry.qualityCheckSupported)
    ).toBe(true)
    await nextTick()
  })

  it('hints at a missing required file until the batch has test data, then flags it', () => {
    const store = seededStore()
    store.importRows([
      { id: 'B1', investigator: 'X' },
      { id: 'B2', investigator: 'X' }
    ])
    const [first, second] = store.rows
    // Nothing attached anywhere yet: a hint on both, and no submission.
    for (const row of store.rows) {
      expect(store.activeIssuesFor(row.uid)).toHaveLength(0)
      expect(store.todoFor(row.uid).map((issue) => issue.message)).toEqual([
        MISSING_REQUIRED_MESSAGE
      ])
      expect(store.kindStatus(row.uid, FORCE_DISPLACEMENT)).toBe('todo')
    }
    expect(store.awaitingTestDataCount).toBe(2)
    expect(store.fileErrorCount).toBe(0)
    expect(store.withoutTestDataCount).toBe(0)

    // The first file arrives: the other experiment's slot is now a problem.
    attachTestData(store, first.uid)
    expect(store.kindStatus(first.uid, FORCE_DISPLACEMENT)).toBe('ok')
    const error = store.activeIssuesFor(second.uid).find((issue) => issue.kindKey !== undefined)
    expect(error?.level).toBe('error')
    expect(error?.kindKey).toBe('force_displacement')
    expect(error?.message).toBe(MISSING_REQUIRED_MESSAGE)
    expect(store.kindStatus(second.uid, FORCE_DISPLACEMENT)).toBe('missing_required')
    expect(store.awaitingTestDataCount).toBe(0)
    expect(store.fileErrorCount).toBe(1)
    expect(store.withoutTestDataCount).toBe(1)
    // Errors cannot be dismissed away.
    store.dismissIssue(error!.key)
    expect(store.activeIssuesFor(second.uid)).toHaveLength(1)
    attachTestData(store, second.uid)
    expect(store.activeIssuesFor(second.uid)).toHaveLength(0)
    expect(store.fileErrorCount).toBe(0)
    expect(store.withoutTestDataCount).toBe(0)
    // A fresh import starts over with hints.
    store.importRows([{ id: 'B3', investigator: 'X' }])
    expect(store.kindStatus(store.rows[0].uid, FORCE_DISPLACEMENT)).toBe('todo')
  })

  it('never lets a batch through while a required file is still a hint', async () => {
    const store = seededStore()
    const row = store.rows[0]
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
    await nextTick()
    store.status = 'pass'
    expect(store.awaitingTestDataCount).toBe(1)
    expect(store.canSubmit).toBe(false)
  })

  it('only warns about missing test data when the database requires none', () => {
    const dictionary = useDictionaryStore()
    dictionary.columns = { braces: BRACE_COLUMNS, connections: BRACE_COLUMNS }
    dictionary.state = 'ready'
    const store = useContributionStore()
    store.selectDatabase('connections')
    store.addRow()
    store.settle()
    const row = store.rows[0]
    row.cells.id = 'C1'
    row.cells.investigator = 'X'
    const kinds = timeSeriesKindsFor('connections')
    expect(kinds.every((kind) => !kind.required)).toBe(true)
    const warning = store.activeIssuesFor(row.uid).find((issue) => issue.kindKey === null)
    expect(warning?.level).toBe('warn')
    expect(warning?.message).toBe(NO_TEST_DATA_MESSAGE)
    expect(kinds.map((kind) => store.kindStatus(row.uid, kind))).toEqual(kinds.map(() => 'missing'))
    expect(store.withoutTestDataCount).toBe(1)
    store.dismissIssue(warning!.key)
    expect(store.dismissedWarningMessages).toEqual([`C1: ${NO_TEST_DATA_MESSAGE}`])
    expect(store.withoutTestDataCount).toBe(0)
    store.attachSeries(row.uid, kinds[0], 'C1.csv', 'Chord Rotation [rads],Moment [kN-mm]\n0,0\n')
    expect(store.activeIssuesFor(row.uid)).toHaveLength(0)
    expect(store.dismissedIssuesFor(row.uid)).toHaveLength(0)
  })

  it('keeps a file with errors, blocks on them, and lets a range warning be dismissed', () => {
    const store = seededStore()
    const row = store.rows[0]
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
    attachTestData(store, row.uid, 'B1.csv', 'Displacement [mm],Load [kN]\n0,0\n1,10\n')
    expect(store.timeSeries[`${row.uid}:force_displacement`]?.rows).toBe(2)
    const error = store.activeIssuesFor(row.uid).find((issue) => issue.level === 'error')
    expect(error?.message).toContain('Force [kN]')
    expect(store.kindStatus(row.uid, FORCE_DISPLACEMENT)).toBe('error')
    expect(store.fileErrorCount).toBe(1)

    // Forces in N instead of kN: kept, but worth a look.
    attachTestData(store, row.uid, 'B1.csv', 'Displacement [mm],Force [kN]\n0,0\n1,1500000\n')
    const warning = store.activeIssuesFor(row.uid).find((issue) => issue.level === 'warn')
    expect(warning?.message).toContain('far above')
    expect(store.kindStatus(row.uid, FORCE_DISPLACEMENT)).toBe('warn')
    expect(store.fileErrorCount).toBe(0)
    store.dismissIssue(warning!.key)
    expect(store.kindStatus(row.uid, FORCE_DISPLACEMENT)).toBe('ok')
    // A new file is a new question.
    attachTestData(store, row.uid, 'B1.csv', 'Displacement [mm],Force [kN]\n0,0\n1,2500000\n')
    expect(store.kindStatus(row.uid, FORCE_DISPLACEMENT)).toBe('warn')
  })

  it('tidies an attached file for the data repository', () => {
    const store = seededStore()
    const row = store.rows[0]
    row.cells.id = 'B1'
    attachTestData(store, row.uid, 'B1.csv', '\uFEFFDisplacement [mm],Force [kN]\r\n0,0\r\n1,10')
    expect(store.timeSeries[`${row.uid}:force_displacement`]?.content).toBe(
      'Displacement [mm],Force [kN]\n0,0\n1,10\n'
    )
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
    expect(warning?.message).toContain('"B1.csv"')
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
      // bad area, blank investigator, no force-displacement file
      { uid: second.uid, index: 1, id: 'B2', errors: 2, warnings: 1, issues: 3 },
      { uid: third.uid, index: 2, id: '', errors: 1, warnings: 1, issues: 2 } // blank investigator warns
    ])
    expect(store.activeErrorCount).toBe(3)
    for (const issue of store.activeIssuesFor(second.uid)) store.dismissIssue(issue.key)
    const [remaining] = store.problemSummary
    expect([remaining.errors, remaining.warnings]).toEqual([2, 0])
    // The problems travel with the summary, so the bar can show them in place.
    expect(remaining.issues.map((issue) => issue.column ?? issue.kindKey)).toEqual([
      'area',
      'force_displacement'
    ])
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

describe('contribution store — bulk intake', () => {
  beforeEach(() => setActivePinia(createPinia()))

  function plan(overrides: Partial<IntakePlan> = {}): IntakePlan {
    return {
      primary: null,
      primaryCandidates: [],
      matched: [],
      pending: [],
      skipped: [],
      noise: 0,
      ...overrides
    }
  }
  const CURVE = 'Displacement [mm],Force [kN]\n0,0\n1,10\n'
  const intakeFile = (path: string) => ({
    path,
    name: path.slice(path.lastIndexOf('/') + 1),
    size: 0,
    text: async () => CURVE
  })

  it('merges rows by id, keeping the attachments of the ones it updates', () => {
    const store = seededStore()
    store.importRows([{ id: 'B1', area: '10' }, { id: 'B2' }])
    attachTestData(store, store.rows[0].uid)
    const counts = store.mergeRows([{ id: 'B1', area: '11' }, { id: 'B3' }, { id: '' }])
    expect(counts).toEqual({ added: 2, updated: 1 })
    expect(store.rows.map((row) => row.cells.id)).toEqual(['B1', 'B2', 'B3', ''])
    expect(store.rows[0].cells.area).toBe('11')
    expect(store.timeSeries[`${store.rows[0].uid}:force_displacement`]).toBeDefined()
    expect(store.rows.some((row) => store.isDraft(row.uid))).toBe(false)
  })

  it('applies a plan: primary rows first, so files can land on the new experiments', () => {
    const store = seededStore()
    store.importRows([])
    const summary = store.applyIntake(
      plan({
        primary: {
          file: intakeFile('braces/steel_braces.csv'),
          table: { rows: [{ id: 'B1' }, { id: 'B2' }], matched: ['id'], unknown: [], missing: [] }
        },
        matched: [
          {
            file: intakeFile('braces/force_displacement/B2.csv'),
            kind: FORCE_DISPLACEMENT,
            id: 'B2',
            text: CURVE
          }
        ],
        pending: [
          {
            id: 1,
            file: intakeFile('B9.csv'),
            text: CURVE,
            reason: 'orphan',
            kinds: [FORCE_DISPLACEMENT]
          }
        ],
        skipped: [intakeFile('notes.xlsx')],
        noise: 2
      })
    )
    expect(summary).toMatchObject({
      primaryName: 'steel_braces.csv',
      added: 2,
      updated: 0,
      attached: { force_displacement: 1 },
      skipped: ['notes.xlsx'],
      noise: 2
    })
    expect(store.lastIntake).toEqual(summary)
    const b2 = store.rows.find((row) => row.cells.id === 'B2')!
    expect(store.timeSeries[`${b2.uid}:force_displacement`]?.name).toBe('B2.csv')
    expect(store.pendingFiles.map((entry) => entry.file.name)).toEqual(['B9.csv'])
    // Files have started arriving: the missing one on B1 is now a real error.
    const b1 = store.rows.find((row) => row.cells.id === 'B1')!
    expect(store.kindStatus(b1.uid, FORCE_DISPLACEMENT)).toBe('missing_required')
  })

  it('lets a pending file be placed or ignored, and drops the report with the batch', () => {
    const store = seededStore()
    store.importRows([{ id: 'B1' }])
    const pending = {
      id: 7,
      file: intakeFile('run_07.csv'),
      text: CURVE,
      reason: 'orphan' as const,
      kinds: [FORCE_DISPLACEMENT]
    }
    store.applyIntake(
      plan({ pending: [pending, { ...pending, id: 8, file: intakeFile('x.csv') }] })
    )
    expect(store.pendingFiles).toHaveLength(2)
    store.assignPending(7, store.rows[0].uid, FORCE_DISPLACEMENT)
    expect(store.timeSeries[`${store.rows[0].uid}:force_displacement`]?.name).toBe('run_07.csv')
    store.ignorePending(8)
    expect(store.pendingFiles).toEqual([])
    // A second drop of the same path replaces the earlier pending entry.
    store.applyIntake(plan({ pending: [pending] }))
    store.applyIntake(plan({ pending: [{ ...pending, id: 9 }] }))
    expect(store.pendingFiles.map((entry) => entry.id)).toEqual([9])
    store.selectDatabase('columns')
    expect(store.pendingFiles).toEqual([])
    expect(store.lastIntake).toBeNull()
  })
})

describe('contribution store — drafts', () => {
  const validateData = defaultApi.validateData as unknown as Mock

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    validateData.mockClear()
  })
  afterEach(() => vi.useRealTimers())

  it('shows a hand-added experiment’s blank fields as hints, not problems', () => {
    const store = seededStore(BRACE_COLUMNS, { draft: true })
    const uid = store.rows[0].uid
    expect(store.isDraft(uid)).toBe(true)
    expect(store.checkPaused).toBe(true)
    expect(store.activeErrorCount).toBe(0)
    expect(store.activeWarningCount).toBe(0)
    expect(store.problemSummary).toEqual([])
    expect(store.levelFor(uid)).toBe('pass')
    expect(store.todoFor(uid).map((issue) => issue.column)).toEqual(['id', 'investigator'])
    expect(store.cellIssueFor(uid, 'id')?.level).toBe('todo')
    // Submission still waits for an id; the draft only changes how it is shown.
    expect(store.clientErrorCount).toBe(1)
    expect(store.canSubmit).toBe(false)
  })

  it('still flags what was typed wrong on a draft', async () => {
    const store = seededStore(BRACE_COLUMNS, { draft: true })
    const row = store.rows[0]
    row.cells.area = 'abc'
    row.cells.id = 'a/b'
    await nextTick()
    expect(store.isDraft(row.uid)).toBe(true)
    expect(store.cellIssueFor(row.uid, 'area')?.level).toBe('error')
    expect(store.cellIssueFor(row.uid, 'id')?.level).toBe('error')
    expect(store.activeErrorCount).toBe(2)
    // The blank one is still a hint.
    expect(store.cellIssueFor(row.uid, 'investigator')?.level).toBe('todo')
  })

  it('mutes the missing required file while drafting', async () => {
    const store = seededStore(BRACE_COLUMNS, { draft: true })
    const row = store.rows[0]
    row.cells.id = 'B1'
    await nextTick()
    expect(store.withoutTestDataCount).toBe(0)
    expect(store.fileErrorCount).toBe(0)
    expect(store.todoFor(row.uid).some((issue) => issue.message === MISSING_REQUIRED_MESSAGE)).toBe(
      true
    )
    expect(store.kindStatus(row.uid, FORCE_DISPLACEMENT)).toBe('todo')
    store.settle()
    // Still a hint: no test data has reached the batch yet.
    expect(store.awaitingTestDataCount).toBe(1)
    expect(store.fileErrorCount).toBe(0)
  })

  it('holds the server check back while drafting and runs it after a long pause', async () => {
    const store = seededStore(BRACE_COLUMNS, { draft: true })
    const row = store.rows[0]
    row.cells.id = 'B1'
    await nextTick()
    expect(store.checking).toBe(false)
    vi.advanceTimersByTime(5000)
    expect(validateData).not.toHaveBeenCalled()
    expect(store.status).toBe('idle')

    // Typing shortly before the pause would have ended keeps the draft alive.
    vi.advanceTimersByTime(DRAFT_SETTLE_MS - 10_000)
    row.cells.area = '10'
    await nextTick()
    vi.advanceTimersByTime(10_000)
    expect(store.isDraft(row.uid)).toBe(true)
    expect(validateData).not.toHaveBeenCalled()

    vi.advanceTimersByTime(DRAFT_SETTLE_MS)
    expect(store.isDraft(row.uid)).toBe(false)
    expect(store.checkPaused).toBe(false)
    expect(store.checking).toBe(true)
    await vi.advanceTimersByTimeAsync(2000)
    expect(validateData).toHaveBeenCalledTimes(1)
    expect(store.status).toBe('pass')
  })

  it('settles a draft when the contributor moves on to another experiment', async () => {
    const store = seededStore(BRACE_COLUMNS, { draft: true })
    const first = store.rows[0].uid
    store.rows[0].cells.id = 'B1'
    await nextTick()

    // Adding another experiment ends the first draft.
    const second = store.addRow()
    expect(store.isDraft(first)).toBe(false)
    expect(store.isDraft(second)).toBe(true)
    expect(store.activeWarningCount).toBeGreaterThan(0) // B1's blank investigator, now a warning

    // Editing the first again ends the second draft too.
    store.touch(first)
    expect(store.isDraft(second)).toBe(false)
    expect(store.checkPaused).toBe(false)

    // Editing a draft itself keeps it a draft.
    const third = store.addRow()
    store.touch(third)
    expect(store.isDraft(third)).toBe(true)
    store.settle(third)
    expect(store.isDraft(third)).toBe(false)
  })

  it('settles a draft as soon as every required field is filled', async () => {
    const store = seededStore(BRACE_COLUMNS, { draft: true })
    const row = store.rows[0]
    row.cells.id = 'B1'
    await nextTick()
    expect(store.isDraft(row.uid)).toBe(true)
    row.cells.investigator = 'X'
    await nextTick()
    expect(store.isDraft(row.uid)).toBe(false)
    expect(store.checking).toBe(true)
  })

  it('settles the drafts on an explicit check, and checks once', async () => {
    const store = seededStore(BRACE_COLUMNS, { draft: true })
    const row = store.rows[0]
    row.cells.id = 'B1'
    await nextTick()
    await store.runQualityCheck()
    expect(store.isDraft(row.uid)).toBe(false)
    expect(validateData).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(DRAFT_SETTLE_MS)
    expect(validateData).toHaveBeenCalledTimes(1)
  })

  it('never drafts imported rows; a duplicate starts as one', () => {
    const store = seededStore(BRACE_COLUMNS, { draft: true })
    store.importRows([{ id: 'B1' }, { id: '' }])
    expect(store.checkPaused).toBe(false)
    expect(store.rows.every((row) => !store.isDraft(row.uid))).toBe(true)
    expect(store.activeErrorCount).toBeGreaterThan(0)

    store.duplicateRow(store.rows[0].uid)
    const copy = store.rows[2]
    expect(store.isDraft(copy.uid)).toBe(true)
    expect(store.cellIssueFor(copy.uid, 'id')?.level).toBe('todo')

    store.removeRow(copy.uid)
    expect(store.checkPaused).toBe(false)
  })
})

describe('contribution store — submission', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(postContribution).mockReset()
  })

  /** Edits flush the reset watcher; settle it before handing out a verdict. */
  async function submittableStore() {
    const store = seededStore()
    const row = store.rows[0]
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
    attachTestData(store, row.uid)
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
    expect(store.canSubmit).toBe(false) // the required file is missing
    attachTestData(store, row.uid)
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

    await store.submit()

    expect(store.submitStatus).toBe('submitted')
    expect(store.pullRequestUrl).toBe('https://github.com/x/pull/7')
    expect(store.pullRequestNumber).toBe(7)
    const [, archive] = (postContribution as Mock).mock.calls[0]
    expect(archive).toBeInstanceOf(File)
    // Who submits is not sent any more: the backend takes it from the session.
    expect((postContribution as Mock).mock.calls[0]).toHaveLength(3)
  })

  it('passes dismissed warnings, labelled by specimen id', async () => {
    const store = seededStore()
    const row = store.rows[0]
    row.cells.id = 'B1' // "investigator" left blank -> warning
    attachTestData(store, row.uid)
    const warning = store.activeIssuesFor(row.uid).find((issue) => issue.level === 'warn')
    store.dismissIssue(warning!.key)
    await nextTick()
    store.status = 'warn'
    vi.mocked(postContribution).mockResolvedValue({
      pr_url: 'u',
      pr_number: 1,
      branch: 'b'
    })

    await store.submit()

    const [, , dismissed] = (postContribution as Mock).mock.calls[0]
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

    await store.submit()

    expect(store.submitStatus).toBe('error')
    expect(store.submitError).toBe("Specimen id 'a/b' cannot be used as a file name: rule.")
    // The technical side travels with it, for the details fold and the bug link.
    expect(store.submitFailure?.status).toBe(400)
    expect(store.submitFailure?.operation).toBe('submit')
    expect(store.submitFailure?.database).toBe('braces')
    expect(store.submitFailure?.experiments).toBe(1)
    store.resetSubmission()
    expect(store.submitFailure).toBeNull()
  })

  it('falls back to the archive message only when a 400 carries no detail', async () => {
    const store = await submittableStore()
    vi.mocked(postContribution).mockRejectedValue({
      isAxiosError: true,
      response: { status: 400, data: '<html>bad request</html>' }
    })

    await store.submit()

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

    await store.submit()

    expect(store.submitStatus).toBe('error')
    expect(store.status).toBe('fail')
    expect(store.response?.error_count).toBe(1)
  })

  it('names EBF files after the repository convention in the archive', async () => {
    const dictionary = useDictionaryStore()
    dictionary.columns = { braces: BRACE_COLUMNS, ebf: BRACE_COLUMNS }
    dictionary.state = 'ready'
    const store = useContributionStore()
    store.selectDatabase('ebf')
    store.importRows([{ id: '74', investigator: 'X' }])
    const row = store.rows[0]
    store.attachSeries(
      row.uid,
      timeSeriesKindsFor('ebf')[0],
      'id74.csv',
      'data_ind,gamma_t,V\n1,0,0\n'
    )
    expect(store.activeIssuesFor(row.uid)).toHaveLength(0)
    await nextTick()
    // No validator for EBF, so force the verdict the submit path needs.
    store.status = 'pass'
    vi.mocked(postContribution).mockResolvedValue({ pr_url: 'u', pr_number: 1, branch: 'b' })
    await store.submit()
    const entries = vi.mocked(buildTarGz).mock.calls.at(-1)![0]
    expect(entries.map((entry) => entry.path)).toContain(
      'eccentric_braced_frames/processed_data/id74.csv'
    )
  })

  it('does nothing when the batch is not submittable', async () => {
    const store = seededStore()
    await store.submit()
    expect(postContribution).not.toHaveBeenCalled()
    expect(store.submitStatus).toBe('idle')
  })
})
