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

<script lang="ts">
import SliderMixin from "@/components/commons/sliders/SliderMixin.vue";
import UnitMixin from "@/components/commons/UnitMixin.vue";
import { Component, Mixins, Prop, VModel } from "vue-property-decorator";

@Component
export default class UnitSlider extends Mixins(SliderMixin, UnitMixin) {
  readonly precision = 100;

  @VModel({ type: Number })
  model!: number;
  @Prop({ type: Boolean })
  readonly disabled: boolean | undefined;
  @Prop({ type: String })
  readonly label!: string;
  @Prop({ type: Number })
  readonly min!: number;
  @Prop({ type: Number })
  readonly max!: number;

  get sliderModel(): number {
    return this.model / this.ratio;
  }

  set sliderModel(value: number) {
    this.model = value * this.ratio;
  }

  get textModel(): number {
    return Math.round(this.sliderModel * this.precision) / this.precision;
  }

  set textModel(value: number) {
    this.sliderModel = value;
  }

  get displayedMin(): number {
    return this.min / this.ratio;
  }

  get displayedMax(): number {
    return this.max / this.ratio;
  }
}

export interface UnitSliderItem<K = string> {
  key: K;
  label: string;
  min: number;
  max: number;
  unit?: string;
}

export class Variable {
  public key: string;
  public text: string;
  public unit: string;
  public min: number;
  public max: number;
  constructor(options: {
    key: string;
    text: string;
    unit?: string;
    min: number;
    max: number;
  }) {
    this.key = options.key;
    this.text = options.text;
    this.unit = options.unit ?? "";
    this.min = options.min;
    this.max = options.max;
  }
}
</script>

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
    width: 64px;
  }
}
</style>
