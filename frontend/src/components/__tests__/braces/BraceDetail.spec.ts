import type { BraceModel } from '@/backend'
import BraceDetail from '@/components/braces/BraceDetail.vue'
import i18n from '@/plugins/i18n'
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

vi.mock('@/plugins/axios', () => ({
  bracesApi: new Proxy({}, { get: () => () => Promise.resolve({ data: [] }) })
}))

const render = (brace: Partial<BraceModel>) =>
  mount(BraceDetail, {
    props: { brace: brace as BraceModel },
    global: {
      plugins: [i18n],
      stubs: {
        CommonDetail: { template: '<div><slot name="body" /></div>' },
        PropertyItem: { template: '<p><slot /></p>' },
        VRow: { template: '<div><slot /></div>' },
        VCol: { template: '<div><slot /></div>' },
        ZoomableImage: true
      }
    }
  }).text()

describe('BraceDetail', () => {
  it('says Not Reported for an empty stress', () => {
    expect(render({ f_um: null })).toContain('Not Reported')
    expect(render({ f_um: null })).not.toContain('Not Applicable')
  })

  it('keeps 2 decimals on the measured gusset stresses', () => {
    const text = render({ boundary_condition: 'Gusset plate', f_ym_gp: 508.25, f_um_gp: 600.5 })
    expect(text).toContain('508.25')
    expect(text).toContain('600.50')
  })
})
