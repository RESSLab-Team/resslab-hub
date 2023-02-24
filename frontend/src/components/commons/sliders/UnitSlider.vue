<script setup lang="ts">
import { useColors } from "@/utils/slider";
import { useUnits } from "@/utils/unit";
import { withDefaults, defineProps, defineEmits, computed } from "vue";
import { Color } from "vuetify/lib/util/colors";

export interface UnitSliderItem<K = string> {
  key: K;
  label: string;
  min: number;
  max: number;
  unit?: string;
}

export interface Variable<K extends string = string> {
  key: K;
  text: string;
  unit?: string;
  min: number;
  max: number;
}

const props = withDefaults(
  defineProps<{
    value: number;
    color?: Color;
    unit?: string;
    disabled?: boolean;
    label: string;
    min: number;
    max: number;
  }>(),
  {
    color: undefined,
    unit: undefined,
    disabled: false,
  }
);
const emit = defineEmits<{
  (e: "input", value: number): void;
}>();

const precision = 100;

const { baseColor, darkenColor, lightenColor } = useColors(props.color);
const { ratio, unitLabel } = useUnits(props.unit);

const sliderModel = computed<number>({
  get: () => props.value / ratio.value,
  set: (value) => emit("input", value * ratio.value),
});
const textModel = computed<number>({
  get: () => Math.round(sliderModel.value * precision) / precision,
  set: (value) => (sliderModel.value = value),
});
const displayedMin = computed<number>(() => props.min / ratio.value);
const displayedMax = computed<number>(() => props.max / ratio.value);
</script>

<template>
  <v-sheet class="pa-1" elevation="1" rounded>
    <v-slider
      v-model="sliderModel"
      :color="baseColor"
      dense
      :disabled="disabled"
      hide-details
      :max="displayedMax"
      :min="displayedMin"
      step="0"
      :thumb-color="darkenColor"
      :track-color="lightenColor"
    >
      <template #prepend>
        <v-tooltip bottom>
          <template #activator="{ on, attrs }">
            <div class="mt-0 pt-0 label" v-bind="attrs" v-on="on">
              <!-- eslint-disable-next-line vue/no-v-html -->
              <span v-html="label"></span>
              <template v-if="unitLabel"> [{{ unitLabel }}]</template>
            </div>
          </template>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <span v-html="label"></span>
          <template v-if="unitLabel"> [{{ unitLabel }}]</template>
        </v-tooltip>
      </template>
      <template #append>
        <v-text-field
          v-model="textModel"
          class="mt-0 pt-0"
          dense
          hide-details
          hide-spin-buttons
          :max="displayedMax"
          :min="displayedMin"
          single-line
          type="number"
        ></v-text-field>
      </template>
    </v-slider>
  </v-sheet>
</template>

<style lang="scss" scoped>
.v-input__slider {
  align-items: center;
}
div.label {
  line-height: initial;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.v-input__append-outer,
.v-input__prepend-outer {
  & > div {
    width: 84px;
  }
}
</style>
