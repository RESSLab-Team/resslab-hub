<script setup lang="ts">
import SimpleToggle from '@/components/commons/SimpleToggle.vue'
import { useUnitStore } from '@/stores/unit'
import { unitItems, type UnitSystem } from '@/utils/unit'
import { computed, withDefaults } from 'vue'

const props = withDefaults(
  defineProps<{
    hideUnit?: boolean
  }>(),
  {
    hideUnit: false
  }
)

const unitStore = useUnitStore()

const unitSystem = computed<UnitSystem>({
  get: () => unitStore.unitSystem,
  set: (value) => unitStore.setUnitSystem(value)
})
</script>

<template>
  <v-row>
    <v-col>
      <slot />
    </v-col>
    <v-col v-if="!props.hideUnit" cols="auto">
      <simple-toggle v-model="unitSystem" :items="unitItems" />
    </v-col>
  </v-row>
</template>
