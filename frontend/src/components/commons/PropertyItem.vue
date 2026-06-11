<script setup lang="ts">
const props = defineProps<{
  name: string
  unit?: string
  mono?: boolean
}>()
</script>

<template>
  <div class="prop-item">
    <span class="prop-name">{{ props.name }}:</span>
    <span class="prop-val" :class="{ mono: props.mono }">
      <slot />
      <span v-if="props.unit" class="prop-unit">[{{ props.unit }}]</span>
    </span>
  </div>
</template>
