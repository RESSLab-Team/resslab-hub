import { useDataset } from '@/composables/useDataset'
import { describe, expect, it, vi } from 'vitest'

interface TestModel {
  id: string
  connection_type: string
  t_dp_tot: number
}

const rows: TestModel[] = [
  { id: '1', connection_type: 'WUF-W', t_dp_tot: 10 },
  { id: '2', connection_type: 'RBS', t_dp_tot: 30 },
  { id: '3', connection_type: 'WUF-W', t_dp_tot: 20 },
  { id: '4', connection_type: 'BFP', t_dp_tot: 5 }
]

// Each test binds a unique cache key so the module-level dataset cache doesn't
// bleed between cases.
let keySeq = 0
function bind() {
  const dataset = useDataset<TestModel>(`test-${keySeq++}`, async () => rows)
  return dataset
}

describe('useDataset.pageSync', () => {
  it('returns [] before the dataset has loaded', () => {
    const { pageSync } = bind()
    expect(pageSync(undefined, ['t_dp_tot'], [false], 1, 2)).toEqual([])
  })

  it('filters, sorts and slices synchronously once loaded', async () => {
    const dataset = bind()
    await dataset.ready()

    // ascending by t_dp_tot, first page of 2
    expect(dataset.pageSync(undefined, ['t_dp_tot'], [false], 1, 2).map((r) => r.id)).toEqual([
      '4',
      '1'
    ])
    // second page of 2
    expect(dataset.pageSync(undefined, ['t_dp_tot'], [false], 2, 2).map((r) => r.id)).toEqual([
      '3',
      '2'
    ])
    // descending
    expect(dataset.pageSync(undefined, ['t_dp_tot'], [true], 1, 2).map((r) => r.id)).toEqual([
      '2',
      '3'
    ])
  })

  it('applies the query filter before paging', async () => {
    const dataset = bind()
    await dataset.ready()
    const page = dataset.pageSync('connection_type:WUF-W', ['t_dp_tot'], [false], 1, 10)
    expect(page.map((r) => r.id)).toEqual(['1', '3'])
  })

  it('matches getPage items for the same request', async () => {
    const dataset = bind()
    await dataset.ready()
    const response = await dataset.getPage(undefined, ['t_dp_tot'], [true], 1, 3)
    expect(dataset.pageSync(undefined, ['t_dp_tot'], [true], 1, 3)).toEqual(response.data.items)
  })
})

describe('useDataset crossfilter sync functions', () => {
  it('countsSync returns [] before the dataset has loaded', () => {
    const { countsSync } = bind()
    expect(countsSync(['connection_type'])).toEqual([])
  })

  it('countsSync groups and filters once loaded', async () => {
    const dataset = bind()
    await dataset.ready()
    expect(dataset.countsSync(['connection_type'])).toEqual(
      expect.arrayContaining([
        { names: ['WUF-W'], value: 2 },
        { names: ['RBS'], value: 1 },
        { names: ['BFP'], value: 1 }
      ])
    )
    expect(dataset.countsSync(['connection_type'], 't_dp_tot:>15')).toEqual(
      expect.arrayContaining([
        { names: ['WUF-W'], value: 1 },
        { names: ['RBS'], value: 1 }
      ])
    )
  })

  it('countRowsSync counts the filtered set', async () => {
    const dataset = bind()
    await dataset.ready()
    expect(dataset.countRowsSync()).toBe(4)
    expect(dataset.countRowsSync('connection_type:WUF-W')).toBe(2)
  })

  it('matrixSync projects the requested fields with ids', async () => {
    const dataset = bind()
    await dataset.ready()
    const model = dataset.matrixSync(['t_dp_tot'], 'connection_type:WUF-W')
    expect(model.ids).toEqual(['1', '3'])
    expect(model.data).toEqual([[10], [20]])
  })

  it('countsSync matches the async getCounts', async () => {
    const dataset = bind()
    await dataset.ready()
    const response = await dataset.getCounts(['connection_type'], 't_dp_tot:>15')
    expect(dataset.countsSync(['connection_type'], 't_dp_tot:>15')).toEqual(response.data)
  })
})

describe('useDataset cache behaviour', () => {
  it('keeps datasets with different keys isolated', async () => {
    const ds1 = useDataset(`iso-a-${keySeq++}`, async () => [rows[0]])
    const ds2 = useDataset(`iso-b-${keySeq++}`, async () => rows)
    await ds1.ready()
    await ds2.ready()
    expect(ds1.countRowsSync()).toBe(1)
    expect(ds2.countRowsSync()).toBe(4)
  })

  it('dedupes the fetch across bindings of the same key', async () => {
    const fetchAll = vi.fn(async () => rows)
    const key = `dedupe-${keySeq++}`
    const ds1 = useDataset(key, fetchAll)
    const ds2 = useDataset(key, fetchAll)
    await ds1.ready()
    await ds2.ready()
    expect(fetchAll).toHaveBeenCalledTimes(1)
    expect(ds2.countRowsSync()).toBe(4)
  })

  it('evicts a failed fetch so the next binding retries', async () => {
    const key = `retry-${keySeq++}`
    const failing = useDataset(key, async (): Promise<TestModel[]> => {
      throw new Error('network down')
    })
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    await expect(failing.ready()).rejects.toThrow('network down')
    consoleError.mockRestore()

    // Same key, working fetcher: the poisoned entry must have been evicted.
    const retried = useDataset(key, async () => rows)
    await retried.ready()
    expect(retried.countRowsSync()).toBe(4)
  })
})
