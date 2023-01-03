<template>
  <v-responsive aspect-ratio="1.2" :max-width="maxWidth">
    <v-chart
      v-if="hasData"
      autoresize
      :init-options="initOptions"
      :option="option"
      :update-options="updateOptions"
    ></v-chart>
  </v-responsive>
</template>

<script lang="ts">
import { initOptions, updateOptions } from "@/components/commons/charts/utils";
import { primaryColor } from "@/utils/vuetify";
import { AxiosResponse } from "axios";
import { EChartsOption } from "echarts";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import VChart from "vue-echarts";
import { Component, Prop, Vue, Watch } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

use([SVGRenderer, LineChart, GridComponent, TooltipComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class SimpleLineChart extends Vue {
  readonly initOptions = initOptions;
  readonly updateOptions = updateOptions;

  @Prop({ type: Object as () => Color, default: () => primaryColor })
  readonly color!: Color;
  @Prop({ type: Number, default: 300 })
  readonly maxWidth!: number;
  @Prop({ type: Promise })
  readonly promise: Promise<AxiosResponse<number[][]>> | undefined;
  @Prop({ type: String })
  readonly title: string | undefined;
  @Prop({ type: String })
  readonly xAxisName: string | undefined;
  @Prop({ type: String })
  readonly yAxisName: string | undefined;

  private series: number[][] = [];

  created(): void {
    this.onChanged();
  }

  get option(): EChartsOption {
    return {
      title: {
        text: this.title,
        left: "center",
      },
      grid: {
        left: 96,
        top: 64,
        right: 32,
        bottom: 64,
      },
      xAxis: {
        name: this.xAxisName,
        nameLocation: "middle",
        nameTextStyle: {
          fontWeight: "bold",
        },
        nameGap: 32,
        axisLabel: {
          hideOverlap: true,
        },
      },
      yAxis: {
        name: this.yAxisName,
        nameLocation: "middle",
        nameTextStyle: {
          fontWeight: "bold",
        },
        nameGap: 70,
        axisLabel: {
          hideOverlap: true,
        },
      },
      tooltip: {
        trigger: "axis",
        confine: true,
      },
      series: [
        {
          type: "line",
          showSymbol: false,
          lineStyle: {
            width: 1,
          },
          emphasis: {
            lineStyle: {
              width: 1,
            },
          },
          data: this.series,
        },
      ],
      color: this.color.base,
    };
  }

  get hasData(): boolean {
    return this.series.length > 0;
  }

  @Watch("promise")
  onChanged(): void {
    if (this.promise) {
      this.promise
        .then((response) => response.data)
        .then((series) => {
          this.series = series;
        });
    }
  }
}
</script>
