<script setup lang="ts">
import { defineProps, withDefaults, defineEmits, computed } from "vue";
import { ToggleItem } from "@/utils/toggle";

// TODO add genericity https://github.com/vuejs/rfcs/discussions/436
const props = withDefaults(
  defineProps<{
    value: string;
    items?: ToggleItem<string>[];
  }>(),
  {
    items: () => [],
  }
);
const emit = defineEmits<{
  (e: "input", value: string): void;
}>();

const index = computed<number>({
  get: () => props.items.findIndex((item) => item.value === props.value) ?? 0,
  set: (value) => emit("input", props.items[value].value),
});
</script>

<template>
  <v-btn-toggle
    v-model="index"
    class="align-center"
    background-color="transparent"
    dense
    mandatory
  >
    <v-btn v-for="item in items" :key="item.value">{{ item.text }}</v-btn>
  </v-btn-toggle>
</template>
