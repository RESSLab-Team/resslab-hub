<template>
  <v-sheet class="pa-1" elevation="1" rounded>
    <v-slider
      v-model="sliderModel"
      :color="baseColor"
      dense
      hide-details
      :max="displayedMax"
      :min="displayedMin"
      step="0"
      :thumb-color="darkenColor"
      :track-color="lightenColor"
    >
      <template v-slot:prepend>
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
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
      <template v-slot:append>
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
    width: 64px;
  }
}
</style>

<script lang="ts">
import { Component, Mixins, Prop, VModel } from "vue-property-decorator";
import UnitParent from "../UnitParent.vue";
import SliderParent from "./SliderParent.vue";

@Component
export default class UnitSlider extends Mixins(SliderParent, UnitParent) {
  readonly precision = 100;

  @VModel({ type: Number })
  model!: number;
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
</script>
