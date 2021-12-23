<template>
  <v-sheet class="pa-1" elevation="1" rounded>
    <v-slider
      v-model="model"
      :color="baseColor"
      dense
      hide-details=""
      :max="max"
      :min="min"
      :step="step"
      :thumb-color="darkenColor"
      thumb-label
      :track-color="lightenColor"
    >
      <template v-slot:prepend>
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <div class="mt-0 pt-0 label" v-bind="attrs" v-on="on">
              <!-- eslint-disable-next-line vue/no-v-html -->
              <span v-html="label"></span>
              <template v-if="unit"> [{{ unit }}]</template>
            </div>
          </template>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <span v-html="label"></span>
          <template v-if="unit"> [{{ unit }}]</template>
        </v-tooltip>
      </template>
      <template v-slot:append>
        <v-text-field
          v-model="model"
          class="mt-0 pt-0"
          dense
          hide-details
          :max="max"
          :min="min"
          single-line
          type="number"
          :step="step"
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
import { primaryColor } from "@/utils/vuetify";
import { Component, Prop, VModel, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

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
  @Prop({ type: Object as () => Color, default: () => primaryColor })
  readonly color: Color | undefined;

  get baseColor(): string | undefined {
    return this.color?.base;
  }

  get lightenColor(): string | undefined {
    return this.color?.lighten4;
  }

  get darkenColor(): string | undefined {
    return this.color?.darken4;
  }
}
</script>
