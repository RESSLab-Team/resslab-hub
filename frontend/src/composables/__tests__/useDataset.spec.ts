import { useDataset } from '@/composables/useDataset'
import { describe, expect, it } from 'vitest'

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
