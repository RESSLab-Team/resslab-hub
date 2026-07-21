import { parseCsv, readCsvRecord, readCsvTable } from '@/utils/csv'
import { describe, expect, it } from 'vitest'

describe('parseCsv', () => {
  it('splits plain rows', () => {
    expect(parseCsv('a,b\n1,2')).toEqual([
      ['a', 'b'],
      ['1', '2']
    ])
  })

  it('keeps commas and newlines inside quoted fields', () => {
    expect(parseCsv('a,b\n"Kanvinde, Deierlein","line1\nline2"')).toEqual([
      ['a', 'b'],
      ['Kanvinde, Deierlein', 'line1\nline2']
    ])
  })

  it('unescapes doubled quotes', () => {
    expect(parseCsv('a\n"say ""hi"""')).toEqual([['a'], ['say "hi"']])
  })

  it('handles CRLF endings and a missing final newline', () => {
    expect(parseCsv('a,b\r\n1,2\r\n3,4')).toEqual([
      ['a', 'b'],
      ['1', '2'],
      ['3', '4']
    ])
  })

  it('strips a UTF-8 BOM from the first header', () => {
    expect(parseCsv('﻿id,area\nX,1')[0]).toEqual(['id', 'area'])
  })

  it('drops blank lines', () => {
    expect(parseCsv('a,b\n\n1,2\n\n')).toEqual([
      ['a', 'b'],
      ['1', '2']
    ])
  })
})

describe('readCsvRecord', () => {
  const columns = ['id', 'area', 'steel']

  it('maps the first data row onto known columns', () => {
    const record = readCsvRecord('id,area,steel\nBRC-1,4580,A992\n', columns)
    expect(record.values).toEqual({ id: 'BRC-1', area: '4580', steel: 'A992' })
    expect(record.matched).toEqual(['id', 'area', 'steel'])
    expect(record.unknown).toEqual([])
    expect(record.missing).toEqual([])
  })

  it('treats NA and NR as blank rather than importing them literally', () => {
    const record = readCsvRecord('id,area,steel\nBRC-1,NA,nr\n', columns)
    expect(record.values).toEqual({ id: 'BRC-1' })
  })

  it('reports unknown and missing columns without failing', () => {
    const record = readCsvRecord('id,bogus\nBRC-1,x\n', columns)
    expect(record.values).toEqual({ id: 'BRC-1' })
    expect(record.unknown).toEqual(['bogus'])
    expect(record.missing).toEqual(['area', 'steel'])
  })

  it('imports only the first row but reports how many it saw', () => {
    const record = readCsvRecord('id\nBRC-1\nBRC-2\nBRC-3\n', columns)
    expect(record.values).toEqual({ id: 'BRC-1' })
    expect(record.rowCount).toBe(3)
  })

  it('rejects an empty file and a header with no data', () => {
    expect(() => readCsvRecord('', columns)).toThrow(/empty/i)
    expect(() => readCsvRecord('id,area\n', columns)).toThrow(/no data rows/i)
  })
})

describe('readCsvTable', () => {
  const columns = ['id', 'area', 'steel']

  it('reads every row and aligns to the columns', () => {
    const table = readCsvTable('id,area\nB1,10\nB2,20\n', columns)
    expect(table.rows).toEqual([
      { id: 'B1', area: '10' },
      { id: 'B2', area: '20' }
    ])
    expect(table.matched).toEqual(['id', 'area'])
    expect(table.missing).toEqual(['steel'])
  })

  it('collapses NR to blank but keeps NA verbatim', () => {
    const table = readCsvTable('id,area,steel\nB1,NR,NA\n', columns)
    expect(table.rows[0]).toEqual({ id: 'B1', area: '', steel: 'NA' })
  })

  it('handles quoted cells with embedded commas and newlines', () => {
    const table = readCsvTable('id,area\n"B,1","line1\nline2"\n', columns)
    expect(table.rows[0]).toEqual({ id: 'B,1', area: 'line1\nline2' })
  })

  it('drops unknown headers and reports them', () => {
    const table = readCsvTable('id,bogus\nB1,x\n', columns)
    expect(table.rows[0]).toEqual({ id: 'B1' })
    expect(table.unknown).toEqual(['bogus'])
  })
})
