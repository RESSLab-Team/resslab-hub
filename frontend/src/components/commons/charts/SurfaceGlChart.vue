<template>
  <v-responsive :aspect-ratio="aspectRatio">
    <v-chart
      autoresize
      :option="actualOption"
      :update-options="updateOptions"
    ></v-chart>
  </v-responsive>
</template>

<script lang="ts">
import UnitMixin from "@/components/commons/UnitMixin.vue";
import { EChartsGlOption } from "@/utils/echarts-gl";
import { SetOptionOpts } from "echarts";
import { SurfaceChart } from "echarts-gl/charts";
import { Grid3DComponent } from "echarts-gl/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { merge } from "lodash";
import VChart from "vue-echarts";
import { Component, Prop, Vue } from "vue-property-decorator";

use([CanvasRenderer, SurfaceChart, Grid3DComponent]);

@Component({
  components: {
    VChart,
    UnitMixin,
  },
})
export default class SurfaceGlChart extends Vue {
  readonly updateOptions: SetOptionOpts = {
    notMerge: true,
  };

  @Prop({ type: Object as () => EChartsGlOption })
  readonly option!: EChartsGlOption;
  @Prop({ type: Number, default: 1 })
  readonly aspectRatio!: number;

  /**
   * https://echarts.apache.org/en/option-gl.html
   */
  get actualOption(): EChartsGlOption {
    const changedOption: EChartsGlOption = {
      grid3D: {
        viewControl: {
          distance: 320,
        },
      },
    };
    return merge({}, this.option, changedOption);
  }
}
</script>
