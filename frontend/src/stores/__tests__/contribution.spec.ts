import { useContributionStore } from '@/stores/contribution'
import { buildCsv, CONTRIBUTION_DATABASES } from '@/utils/contribution'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

describe('buildCsv (multi-row)', () => {
  it('writes the header in dictionary order and one row per experiment', () => {
    const columns = CONTRIBUTION_DATABASES.braces.columns
    const csv = buildCsv('braces', [{ id: 'B1', area: '10' }, { id: 'B2' }])
    const lines = csv.trimEnd().split('\n')
    expect(lines[0]).toBe(columns.join(','))
    expect(lines.length - 1).toBe(2)
    // Blank cells become NR.
    expect(lines[2].split(',')[columns.indexOf('area')]).toBe('NR')
    expect(lines[1].split(',')[columns.indexOf('id')]).toBe('B1')
  })
})

describe('contribution store — experiment rows', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('starts with one row and resets rows on database change', () => {
    const store = useContributionStore()
    expect(store.rows.length).toBe(1)
    store.selectDatabase('braces')
    store.rows[0].cells.id = 'B1'
    store.selectDatabase('columns')
    expect(store.rows.length).toBe(1)
    expect(store.rows[0].cells.id).toBeUndefined()
  })

  it('adds, duplicates (clearing id) and removes rows', () => {
    const store = useContributionStore()
    store.selectDatabase('braces')
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
    expect(store.rows.some((r) => r.uid === keep)).toBe(true)
    expect(store.rows.length).toBe(2)
  })

  it('always keeps at least one row', () => {
    const store = useContributionStore()
    store.selectDatabase('braces')
    store.removeRow(store.rows[0].uid)
    expect(store.rows.length).toBe(1)
  })

  it('drops a row’s attached time-series when it is removed', () => {
    const store = useContributionStore()
    store.selectDatabase('braces')
    const uid = store.rows[0].uid
    store.timeSeries[`${uid}:force_displacement`] = { name: 'x.csv', content: 'a\n1', rows: 1 }
    store.addRow()
    store.removeRow(uid)
    expect(store.timeSeries[`${uid}:force_displacement`]).toBeUndefined()
  })

  it('imports rows and counts client-side errors', () => {
    const store = useContributionStore()
    store.selectDatabase('braces')
    store.importRows([
      { id: 'B1', area: 'not-a-number' },
      { id: '' } // missing id -> error
    ])
    expect(store.rows.length).toBe(2)
    expect(store.experimentCount).toBe(2)
    expect(store.specimenIds).toEqual(['B1'])
    // area error + missing-id error
    expect(store.clientErrorCount).toBeGreaterThanOrEqual(2)
  })
})
