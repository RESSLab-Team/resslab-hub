<script setup lang="ts">
import { computed } from 'vue'

/**
 * Two-tone eyebrow content (handoff `.ed-eyebrow`): the text is split on its
 * first "·" — the primary segment renders red, the remaining qualifier muted.
 * Render inside an eyebrow-classed wrapper, e.g.
 *   <div class="eyebrow"><eyebrow-text :text="eyebrow" /></div>
 * A label with no "·" simply renders all-red.
 */
const props = defineProps<{ text: string }>()

const parts = computed(() => {
  const i = props.text.indexOf('·')
  if (i === -1) return { red: props.text.trim(), mut: '' }
  return { red: props.text.slice(0, i).trim(), mut: props.text.slice(i).trim() }
})
</script>

<template>
  <span class="ey-red">{{ parts.red }}</span
  ><span v-if="parts.mut" class="ey-mut">&nbsp;{{ parts.mut }}</span>
</template>
