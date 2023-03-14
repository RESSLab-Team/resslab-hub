<script setup lang="ts">
const props = defineProps<{
  name: string
  unit?: string
}>()
</script>

<template>
  <div>
    <span class="text--primary">{{ props.name }}: </span>
    <slot />
    <template v-if="props.unit">[{{ props.unit }}]</template>
  </div>
</template>
