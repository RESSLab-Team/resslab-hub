<script setup lang="ts">
import TextSubscript from '@/components/commons/TextSubscript.vue'

const props = defineProps<{
  name: string
  unit?: string
  mono?: boolean
}>()
</script>

<template>
  <div class="prop-item">
    <!-- The name can be a dictionary symbol with <sub>/<sup> (#328). -->
    <span class="prop-name"><text-subscript :text="props.name" /></span>
    <span class="prop-val" :class="{ mono: props.mono }">
      <slot />
      <span v-if="props.unit" class="prop-unit">{{ props.unit }}</span>
    </span>
  </div>
</template>
