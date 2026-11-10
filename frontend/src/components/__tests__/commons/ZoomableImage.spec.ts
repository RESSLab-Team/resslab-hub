import ZoomableImage from '@/components/commons/ZoomableImage.vue'
import en from '@/locales/en.json'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'

const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

// The real v-dialog teleports to the body and animates; the stub shows its
// content while open, which is all these tests need.
const VDialog = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: `<div>
    <slot name="activator" :props="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue" class="dialog-stub"><slot /></div>
  </div>`
}

function mountImage() {
  return mount(ZoomableImage, {
    props: { src: '/img/brace.png', alt: 'Brace end condition', caption: 'A caption' },
    global: {
      plugins: [i18n, createVuetify({ components })],
      stubs: { VDialog }
    }
  })
}

describe('ZoomableImage', () => {
  it('is a button labelled from the alt text', () => {
    const button = mountImage().find('button.zoom-image')
    expect(button.attributes('aria-label')).toBe('Open Brace end condition full size')
    expect(button.find('img').attributes('src')).toBe('/img/brace.png')
  })

  it('opens the image full size on click, and closes with the close button', async () => {
    const wrapper = mountImage()
    expect(wrapper.find('.dialog-stub').exists()).toBe(false)

    await wrapper.find('button.zoom-image').trigger('click')
    const full = wrapper.find('.dialog-stub img.zoom-full')
    expect(full.attributes('src')).toBe('/img/brace.png')
    expect(full.attributes('alt')).toBe('Brace end condition')
    expect(wrapper.find('.zoom-caption').text()).toBe('A caption')

    await wrapper.find('.dialog-stub button[aria-label="Close"]').trigger('click')
    expect(wrapper.find('.dialog-stub').exists()).toBe(false)
  })

  it('passes an image error on, for the callers that fall back', async () => {
    const wrapper = mountImage()
    await wrapper.find('button.zoom-image img').trigger('error')
    expect(wrapper.emitted('error')).toHaveLength(1)
  })
})
