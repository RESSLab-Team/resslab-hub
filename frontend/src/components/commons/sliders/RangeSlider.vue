<script setup lang="ts">
import { useColor } from "@/composables/color";
import { withDefaults, defineProps, defineEmits, computed } from "vue";
import { Color } from "vuetify/lib/util/colors";

const props = withDefaults(
  defineProps<{
    value?: [number, number];
    min: number;
    max: number;
    step?: number;
    color?: Color;
  }>(),
  {
    value: undefined,
    step: 1,
    color: undefined,
  }
);
const emit = defineEmits<{
  (e: "input", value: [number, number]): void;
}>();

const { baseColor, darkenColor, lightenColor } = useColor(props.color);

const actualMin = computed<number>(() => props.min - (props.min % props.step));
const actualMax = computed<number>(
  () => Math.ceil(props.max / props.step) * props.step
);
const range = computed<[number, number]>({
  get: () => props.value ?? [actualMin.value, actualMax.value],
  set: (value) =>
    emit("input", [
      Math.max(actualMin.value, value[0]),
      Math.min(actualMax.value, value[1]),
    ]),
});
const vTextBind = computed(() => ({
  class: "mt-0 pt-0",
  hideDetails: true,
  hideSpinButtons: true,
  min: actualMin.value,
  max: actualMax.value,
  type: "number",
  singleLine: true,
  style: "width: 60px",
}));

function onRangeChanged(value: [number, number] = range.value): void {
  range.value = value;
}

function onMinChanged(min: string): void {
  range.value = [Number(min), range.value[1]];
}

function onMaxChanged(max: string): void {
  range.value = [range.value[0], Number(max)];
}
</script>

<template>
  <v-range-slider
    :value="range"
    class="align-center"
    :color="baseColor"
    hide-details
    :min="actualMin"
    :max="actualMax"
    :step="step"
    :thumb-color="darkenColor"
    :track-color="lightenColor"
    @end="onRangeChanged"
  >
    <template #prepend>
      <v-text-field
        v-bind="vTextBind"
        :value="range[0]"
        @change="onMinChanged"
      />
    </template>
    <template #append>
      <v-text-field
        v-bind="vTextBind"
        :value="range[1]"
        @change="onMaxChanged"
      />
    </template>
  </v-range-slider>
</template>
