<script setup lang="ts">
import { CP_ICON_PATHS, type CpIconName } from '@/components/contribute/icons'

withDefaults(defineProps<{ name: CpIconName; size?: number; width?: number }>(), {
  size: 16,
  width: 2
})
</script>

<template>
  <svg
    :height="size"
    :width="size"
    aria-hidden="true"
    fill="none"
    focusable="false"
    viewBox="0 0 24 24"
  >
    <path
      :d="CP_ICON_PATHS[name]"
      :stroke-width="width"
      stroke="currentColor"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
</template>
