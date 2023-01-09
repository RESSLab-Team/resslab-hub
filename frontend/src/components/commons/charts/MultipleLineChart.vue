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
import { primaryColor, secondaryColor } from "@/utils/vuetify";
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
export default class MultipleLineChart extends Vue {
  readonly initOptions = initOptions;
  readonly updateOptions = updateOptions;

  @Prop({
    type: Array as () => Color[],
    default: () => [primaryColor, secondaryColor],
  })
  readonly colors!: Color[];
  @Prop({ type: Number, default: 300 })
  readonly maxWidth!: number;
  @Prop({
    type: Array as () => Promise<Response>[],
    default: () => [],
  })
  readonly promises!: Promise<Response>[];
  @Prop({ type: String })
  readonly title: string | undefined;
  @Prop({ type: String })
  readonly xAxisName: string | undefined;
  @Prop({ type: String })
  readonly yAxisName: string | undefined;

  private seriesData: number[][][] = [];

  created(): void {
    this.onPromisesChanged();
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
      series: this.seriesData
        .filter((data) => data !== undefined)
        .map((data) => ({
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
          data: data,
        })),
      color: this.colors.map((color) => color.base),
    };
  }

  get hasData(): boolean {
    return this.seriesData.filter((data) => data.length > 0).length > 0;
  }

  @Watch("promises")
  onPromisesChanged(): void {
    Promise.all(this.promises).then(
      (promises) =>
        (this.seriesData = promises.map((response) =>
          Array.isArray(response) ? response : response.data
        ))
    );
  }
}

export type Response = AxiosResponse<number[][]> | number[][];
</script>
