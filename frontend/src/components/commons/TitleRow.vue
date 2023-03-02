<script setup lang="ts">
import { defineProps, withDefaults, computed } from "vue";
import { useUnitStore } from "@/stores/unit";
import { UnitSystem, unitItems } from "@/utils/unit";
import SimpleToggle from "./SimpleToggle.vue";

const props = withDefaults(
  defineProps<{
    showUnitToggle?: boolean;
  }>(),
  {
    showUnitToggle: true,
  }
);

const unitStore = useUnitStore();
const unitSystem = computed<UnitSystem>({
  get: () => unitStore.unitSystem,
  set: (value) => unitStore.setUnitSystem(value),
});
</script>

<template>
  <v-row>
    <v-col>
      <slot></slot>
    </v-col>
    <v-col v-if="props.showUnitToggle" cols="auto">
      <v-spacer></v-spacer>
      <simple-toggle v-model="unitSystem" :items="unitItems" />
    </v-col>
  </v-row>
</template>
