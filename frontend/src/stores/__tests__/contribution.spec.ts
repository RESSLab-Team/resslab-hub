import { useContributionStore } from '@/stores/contribution'
import { useDictionaryStore, type DictColumn } from '@/stores/dictionary'
import { buildCsv } from '@/utils/contribution'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

const BRACE_COLUMNS: DictColumn[] = [
  { name: 'id', description: '', symbol: '', unit: '-', type: 'String', example: 'B1', nullable: false },
  { name: 'area', description: '', symbol: '', unit: 'mm2', type: 'Numeric', example: '10', nullable: true },
  { name: 'investigator', description: '', symbol: '', unit: '-', type: 'String', example: 'X', nullable: false }
]

function seededStore(columns: DictColumn[] = BRACE_COLUMNS) {
  const dictionary = useDictionaryStore()
  dictionary.columns = { braces: columns }
  dictionary.state = 'ready'
  const store = useContributionStore()
  store.selectDatabase('braces')
  return store
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
      { name: 'cycles', description: '', symbol: '', unit: '-', type: 'Integer', example: '2', nullable: true }
    ])
    const row = store.rows[0]
    row.cells.id = 'B1'
    row.cells.investigator = 'X'
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
