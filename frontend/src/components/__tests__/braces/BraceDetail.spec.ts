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
  // #427: the record's not_reported list says why a stress is empty.
  it('says Not reported for an empty stress the record lists', () => {
    const text = render({ f_yn: 345, fy_m: 400, f_um: null, not_reported: ['f_um'] })
    expect(text).toContain('Not reported')
    expect(text).not.toContain('Not applicable')
  })

  it('says Not applicable for an empty gusset stress the record does not list', () => {
    const text = render({
      boundary_condition: 'Gusset plate',
      f_yn: 345,
      fy_m: 400,
      f_um: 500,
      f_yn_gp: null,
      f_ym_gp: 508.25,
      f_um_gp: 600.5,
      not_reported: []
    })
    expect(text).toContain('Not applicable')
    expect(text).not.toContain('Not reported')
  })

  it('keeps 2 decimals on the measured gusset stresses', () => {
    const text = render({ boundary_condition: 'Gusset plate', f_ym_gp: 508.25, f_um_gp: 600.5 })
    expect(text).toContain('508.25')
    expect(text).toContain('600.50')
  })
})
