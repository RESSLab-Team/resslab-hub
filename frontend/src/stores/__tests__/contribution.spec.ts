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

function seededStore() {
  const dictionary = useDictionaryStore()
  dictionary.columns = { braces: BRACE_COLUMNS }
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
