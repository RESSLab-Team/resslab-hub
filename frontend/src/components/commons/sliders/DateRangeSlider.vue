<script setup lang="ts">
import {
  withDefaults,
  defineProps,
  computed,
  defineEmits,
  ref,
  onMounted,
  watch,
} from "vue";
import { Color } from "vuetify/lib/util/colors";
import { useColors } from "@/utils/slider";
import { mapDateToNumber, mapNumberToDate } from "@/utils/date";

const props = withDefaults(
  defineProps<{
    value?: [string, string];
    min: string;
    max: string;
    color?: Color;
  }>(),
  {
    value: undefined,
    color: undefined,
  }
);
const emit = defineEmits<{
  (e: "input", value: [string, string]): void;
}>();

const { baseColor, darkenColor, lightenColor } = useColors(props.color);

const pickerdialog = ref(false);
const pickerRange = ref<[string, string] | [string]>();

const range = computed<[string, string]>({
  get: () => props.value ?? [props.min, props.max],
  set: (value) => emit("input", value),
});
const rangeNumber = computed<[number, number]>({
  get: () => range.value.map(mapDateToNumber) as [number, number],
  set: (value) =>
    (range.value = value.map(mapNumberToDate) as [string, string]),
});
const maxNumber = computed(() => mapDateToNumber(props.max));
const minNumber = computed(() => mapDateToNumber(props.min));

onMounted(() => {
  pickerRange.value = range.value;
});

watch(pickerRange, (value) => {
  if (value) {
    range.value = value.length === 1 ? [value[0], value[0]] : value;
  }
});

function onRangeNumberChange(value: [number, number]) {
  rangeNumber.value = value;
}

function onTextClick() {
  pickerdialog.value = true;
}
</script>

<template>
  <div>
    <v-range-slider
      :value="rangeNumber"
      class="align-center"
      :color="baseColor"
      hide-details
      :min="minNumber"
      :max="maxNumber"
      :thumb-color="darkenColor"
      :track-color="lightenColor"
      @end="onRangeNumberChange"
    >
      <template #prepend>
        <v-text-field
          :value="range[0]"
          class="mt-0 pt-0"
          hide-details
          readonly
          single-line
          style="width: 82px"
          @click="onTextClick"
        />
      </template>
      <template #append>
        <v-text-field
          :value="range[1]"
          class="mt-0 pt-0"
          hide-details
          readonly
          single-line
          style="width: 82px"
          @click="onTextClick"
        />
      </template>
    </v-range-slider>
    <v-dialog v-model="pickerdialog" max-width="300">
      <v-date-picker v-model="pickerRange" :min="min" :max="max" range />
    </v-dialog>
  </div>
</template>
