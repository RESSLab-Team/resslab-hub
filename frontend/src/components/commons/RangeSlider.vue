<template>
  <v-range-slider
    v-model="range"
    class="align-center"
    :color="baseColor"
    hide-details
    :min="min"
    :max="max"
    :step="step"
    thumb-label
    :track-color="lightenColor"
    @end="onRangeChange"
  >
    <template v-slot:prepend>
      <v-text-field
        :value="range[0]"
        class="mt-0 pt-0"
        hide-details
        :min="min"
        type="number"
        single-line
        style="width: 60px"
        @change="onChangeMin"
      ></v-text-field>
    </template>
    <template v-slot:append>
      <v-text-field
        :value="range[1]"
        class="mt-0 pt-0"
        hide-details
        :max="max"
        type="number"
        single-line
        style="width: 60px"
        @change="onChangeMax"
      ></v-text-field>
    </template>
  </v-range-slider>
</template>

<script lang="ts">
import { RangeModel } from "@/backend";
import { AxiosResponse } from "axios";
import { Component, Prop, Vue, Watch } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component
export default class RangeSlider extends Vue {
  @Prop({ type: Array })
  readonly value: [number, number] | undefined;
  @Prop({ type: Promise })
  readonly getRange: Promise<AxiosResponse<RangeModel>> | undefined;
  @Prop({ type: Number, default: 1 })
  readonly step!: number;
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;

  min = 0;
  max = 0;
  range: [number, number] = [this.min, this.max];

  get baseColor(): string | undefined {
    return this.color?.base;
  }

  get lightenColor(): string | undefined {
    return this.color?.lighten4;
  }

  created(): void {
    this.onGetRangeChanged();
  }

  @Watch("getRange")
  onGetRangeChanged(): void {
    if (this.getRange) {
      this.getRange
        .then((res) => res.data)
        .then((range) => {
          const oldMin = this.min;
          const oldMax = this.max;
          this.min = range.min - (range.min % this.step);
          this.max = Math.ceil(range.max / this.step) * this.step;
          if (this.range[0] === oldMin || this.range[0] < this.min) {
            this.$set(this.range, 0, this.min);
          }
          if (this.range[1] === oldMax || this.range[1] > this.max) {
            this.$set(this.range, 1, this.max);
          }
        });
    }
  }

  @Watch("value")
  onValueChanged(): void {
    if (this.value == undefined) {
      this.range = [this.min, this.max];
    } else {
      this.range = [
        Math.max(this.min, this.value[0]),
        Math.min(this.max, this.value[1]),
      ];
    }
  }

  onRangeChange(): void {
    this.$emit("input", this.range);
  }

  onChangeMin(min: number): void {
    this.$set(this.range, 0, min);
    this.onRangeChange();
  }

  onChangeMax(max: number): void {
    this.$set(this.range, 1, max);
    this.onRangeChange();
  }
}
</script>
