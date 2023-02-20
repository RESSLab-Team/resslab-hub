<script setup lang="ts">
import { SelectItem } from "@/utils/vuetify";
import { withDefaults, defineProps, computed, defineEmits } from "vue";

const props = withDefaults(
  defineProps<{
    value?: string;
    items?: SelectItem[];
    prefix?: string;
  }>(),
  {
    value: "",
    items: () => [],
    prefix: "",
  }
);
const emit = defineEmits<{
  (e: "input", value: string): void;
}>();

const item = computed<string>({
  get: () => props.value,
  set: (value) => emit("input", value),
});
</script>

<template>
  <v-select v-model="item" :items="items" hide-details>
    <template #selection="data">
      {{ $t(prefix + data.item) }}
    </template>
    <template #item="data">
      {{ $t(prefix + data.item) }}
    </template>
  </v-select>
</template>
