<template>
  <v-slider v-model="model" :max="max" :min="min" :step="step" thumb-label>
    <template v-slot:label>
      <!-- eslint-disable-next-line vue/no-v-html -->
      <span v-html="label"></span>
      <template v-if="unit"> [{{ unit }}]</template>
    </template>
    <template v-slot:append>
      <v-text-field
        v-model="model"
        class="mt-0 pt-0"
        hide-details
        single-line
        type="number"
        style="width: 60px"
      ></v-text-field>
    </template>
  </v-slider>
</template>

<script lang="ts">
import { Component, Prop, VModel, Vue } from "vue-property-decorator";

@Component
export default class UnitSlider extends Vue {
  @VModel({ type: Number })
  readonly model!: number;
  @Prop({ type: String })
  readonly label!: string;
  @Prop({ type: String })
  readonly unit: string | undefined;
  @Prop({ type: Number })
  readonly min!: number;
  @Prop({ type: Number })
  readonly max!: number;
  @Prop({ type: Number, default: 0 })
  readonly step!: number;
}
</script>
