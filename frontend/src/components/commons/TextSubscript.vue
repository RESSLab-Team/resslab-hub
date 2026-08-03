<script lang="ts">
/** Plain text with the `<sub>`/`<sup>` markup removed — for contexts that
 *  can't render the tags (tooltips, canvas width measurement). */
export function stripSubSup(text: string): string {
  return text.replace(/<\/?su[bp]>/g, '')
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ text: string }>()

const substrings = computed(() => {
  const chunks: { text: string; tag?: 'sub' | 'sup' }[] = []
  let match
  let lastIndex = 0
  const regex = /<(sub|sup)>(.*?)<\/\1>/g

  while ((match = regex.exec(props.text)) !== null) {
    if (match.index !== lastIndex) {
      chunks.push({ text: props.text.substring(lastIndex, match.index) })
    }

    chunks.push({ text: match[2], tag: match[1] as 'sub' | 'sup' })

    lastIndex = regex.lastIndex
  }

  if (lastIndex !== props.text.length) {
    chunks.push({ text: props.text.substring(lastIndex) })
  }

  return chunks
})
</script>

<template>
  <span v-for="(substring, index) in substrings" :key="index">
    <component :is="substring.tag" v-if="substring.tag">{{ substring.text }}</component>
    <span v-else>{{ substring.text }}</span>
  </span>
</template>
