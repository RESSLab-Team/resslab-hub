<script setup lang="ts">
/**
 * SI / Imperial unit-system toggle, bound to the global unit store. Extracted
 * from `TitleRow.vue` so the tool-page headers can place it in their actions
 * slot.
 */
import SimpleToggle from '@/components/commons/SimpleToggle.vue'
import { useUnitStore } from '@/stores/unit'
import { unitItems, type UnitSystem } from '@/utils/unit'
import { computed } from 'vue'

const unitStore = useUnitStore()

const unitSystem = computed<UnitSystem>({
  get: () => unitStore.unitSystem,
  set: (value) => unitStore.setUnitSystem(value)
})
</script>

<template>
  <simple-toggle v-model="unitSystem" :items="unitItems" />
</template>
