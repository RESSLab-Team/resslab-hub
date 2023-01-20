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
import { updateOptions } from "@/components/commons/charts/utils";
import UnitMixin from "@/components/commons/UnitMixin.vue";
import { EChartsGlOption } from "@/utils/echarts-gl";
import { SurfaceChart } from "echarts-gl/charts";
import { Grid3DComponent } from "echarts-gl/components";
import { TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { merge, round } from "lodash";
import VChart from "vue-echarts";
import { Component, Prop, Vue } from "vue-property-decorator";

use([CanvasRenderer, SurfaceChart, Grid3DComponent, TooltipComponent]);

@Component({
  components: {
    VChart,
    UnitMixin,
  },
})
export default class SurfaceGlChart extends Vue {
  readonly updateOptions = updateOptions;
  readonly axisLabelMaxDigits = 2;

  @Prop({ type: Object as () => EChartsGlOption })
  readonly option!: EChartsGlOption;
  @Prop({ type: Number, default: 1 })
  readonly aspectRatio!: number;

  /**
   * https://echarts.apache.org/en/option-gl.html
   */
  get actualOption(): EChartsGlOption {
    const defaultOption: EChartsGlOption = {
      tooltip: {
        confine: true,
      },
      grid3D: {
        viewControl: {
          distance: 260,
        },
      },
      xAxis3D: {
        min: "dataMin",
        max: "dataMax",
        axisLabel: {
          formatter: (value) => `${round(value, this.axisLabelMaxDigits)}`,
        },
      },
      yAxis3D: {
        min: "dataMin",
        max: "dataMax",
        axisLabel: {
          formatter: (value) => `${round(value, this.axisLabelMaxDigits)}`,
        },
      },
      zAxis3D: {
        min: "dataMin",
        max: "dataMax",
        axisLabel: {
          formatter: (value) => `${round(value, this.axisLabelMaxDigits)}`,
        },
      },
    };
    return merge(defaultOption, this.option);
  }
}
</script>
