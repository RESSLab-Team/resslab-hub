<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ text: string }>()

const substrings = computed(() => {
  const chunks = []
  let match
  let lastIndex = 0
  const regex = /<sub>(.*?)<\/sub>/g

  while ((match = regex.exec(props.text)) !== null) {
    if (match.index !== lastIndex) {
      chunks.push({
        text: props.text.substring(lastIndex, match.index),
        isSubscript: false
      })
    }

    chunks.push({
      text: match[1],
      isSubscript: true
    })

    lastIndex = regex.lastIndex
  }

  if (lastIndex !== props.text.length) {
    chunks.push({
      text: props.text.substring(lastIndex),
      isSubscript: false
    })
  }

  return chunks
})
</script>

<template>
  <span v-for="(substring, index) in substrings" :key="index">
    <sub v-if="substring.isSubscript">{{ substring.text }}</sub>
    <span v-else>{{ substring.text }}</span>
  </span>
</template>
