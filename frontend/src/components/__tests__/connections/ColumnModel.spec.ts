import ColumnModel from '@/components/columns/ColumnModel.vue'
import { shallowMount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

describe('ColumnComponent.vue', () => {
  it('aisc - W4x13', async () => {
    const radPrecision = 1
    const mmPrecision = -1

    const wrapper = shallowMount(ColumnModel)
    // Drive the inputs the way the UI does: selecting a section syncs the
    // bf/d/tf/tw sliders, then the member/loading sliders are set directly.
    wrapper.vm.onSectionChanged({
      id: 'W4x13',
      bf: 103.124,
      h: 75.438,
      tf: 8.763,
      tw: 7.112,
      ix: 4703415.10928,
      zx: 102255.27936,
      ry: 25.4,
      d: 105.664,
      a: 0,
      iy: 0
    })
    Object.assign(wrapper.vm.variables, { pgPye: 0.2, l: 5000, lb: 5000, fy: 379.225 })
    await nextTick()

    expect(wrapper.vm.vars.ke).toBeCloseTo(1157040, mmPrecision)
    expect(wrapper.vm.vars.my).toBeCloseTo(40134, mmPrecision)

    expect(wrapper.vm.backbone.mc).toBeCloseTo(40134, mmPrecision)
    expect(wrapper.vm.backbone.alpha).toBeCloseTo(0, radPrecision)
    expect(wrapper.vm.backbone.alphaPc).toBeCloseTo(-0.301909128782995, radPrecision)
    expect(wrapper.vm.backbone.lambda).toBeCloseTo(3, radPrecision)

    // First-cycle envelope values match the #212 fix (capping-ratio clamp upper
    // bound 1.3 -> 1.2); the pre-#212 numbers (mc 52175) were stale.
    expect(wrapper.vm.envelope.mc).toBeCloseTo(48161.98, mmPrecision)
    expect(wrapper.vm.envelope.alpha).toBeCloseTo(0.16489396226829972, radPrecision)
    expect(wrapper.vm.envelope.alphaPc).toBeCloseTo(-0.5634907126868205, radPrecision)
  })
})
