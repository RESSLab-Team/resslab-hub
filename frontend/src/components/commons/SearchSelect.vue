<script setup lang="ts">
import { SelectItem } from "@/utils/vuetify";
import {
  withDefaults,
  defineProps,
  defineEmits,
  ref,
  computed,
  unref,
  watch,
} from "vue";

// TODO add genericity https://github.com/vuejs/rfcs/discussions/436
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type V = string | number | object;
const props = withDefaults(
  defineProps<{
    value?: V;
    items?: SelectItem<V>[];
    label?: string;
  }>(),
  {
    value: undefined,
    items: () => [],
    label: undefined,
  }
);
const emit = defineEmits<{
  (e: "input", value?: V): void;
}>();

const search = ref<string>();

const value = computed<V>({
  get: () => props.value,
  set: (value) => emit("input", value),
});
const actualItems = computed<SelectItem[]>(() => {
  const searchValue = unref(search);
  if (!searchValue) {
    return props.items;
  }
  const substring = searchValue.toLowerCase();
  return props.items.filter((item) => {
    const value = typeof item === "string" ? item : item.text.toString();
    return value.toLowerCase().includes(substring);
  });
});
const hint = computed<string>(() => `${actualItems.value.length} items`);

watch(
  () => props.items,
  () => (search.value = undefined)
);
</script>

<template>
  <v-select
    v-model="value"
    clearable
    hide-details
    :items="actualItems"
    :label="label"
    single-line
  >
    <template #prepend-item>
      <v-list-item>
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          clearable
          :hint="hint"
          persistent-hint
          single-line
          solo
        />
      </v-list-item>
    </template>
  </v-select>
</template>
