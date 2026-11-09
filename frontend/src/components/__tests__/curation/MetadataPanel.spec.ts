import type { CurationExperiment } from '@/backend'
import MetadataPanel from '@/components/curation/MetadataPanel.vue'
import i18n from '@/plugins/i18n'
import { useDictionaryStore, type DictColumn } from '@/stores/dictionary'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

function column(name: string, symbol: string): DictColumn {
  // Required and left empty below, so its group opens by itself.
  return { name, description: '', symbol, unit: '-', type: 'Numeric', example: '', nullable: false }
}

describe('MetadataPanel labels', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useDictionaryStore().columns = {
      connections: [column('d_pz', 'd<sub>pz</sub>'), column('specimen_type', 'S<sub>t</sub>')]
    }
  })

  function mountPanel() {
    return mount(MetadataPanel, {
      props: {
        database: 'connections' as const,
        experiment: {
          id: 'X1',
          cells: { d_pz: '', specimen_type: '' }
        } as unknown as CurationExperiment,
        columns: ['d_pz', 'specimen_type']
      },
      global: { plugins: [i18n] }
    })
  }

  it('shows the symbol with a subscript once when the column has no translation', () => {
    const row = mountPanel().find('#field-d_pz .pk')
    expect(row.find('sub').text()).toBe('pz')
    expect(row.findAll('sub')).toHaveLength(1)
    expect(row.find('.symbol').exists()).toBe(false)
  })

  it('keeps the translation and adds the symbol next to it', () => {
    const row = mountPanel().find('#field-specimen_type .pk')
    expect(row.text()).toContain('Specimen Type')
    expect(row.find('.symbol sub').text()).toBe('t')
  })
})
