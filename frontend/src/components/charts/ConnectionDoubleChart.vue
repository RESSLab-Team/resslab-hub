<template>
  <v-chart
    :option="option"
    :update-options="updateOptions"
    @click="onClick"
  ></v-chart>
</template>

<style scoped>
.echarts {
  min-height: 256px;
}
</style>

<script lang="ts">
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import VChart from "vue-echarts";
import { ConnectionColumn, CountModel } from "@/backend";
import { use } from "echarts/core";
import { BarChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { LegendComponent, TooltipComponent } from "echarts/components";
import {
  EChartsOption,
  CallbackDataParams,
  SetOptionOpts,
} from "echarts/types/dist/shared";
import { Searches, unique } from "@/utils/common";
import { isEqual } from "lodash";

use([CanvasRenderer, BarChart, TooltipComponent, LegendComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class ConnectionDoubleChart extends Vue {
  readonly updateOptions: SetOptionOpts = {
    notMerge: true,
  };

  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  fieldSearches!: Searches;
  @Prop({ type: Array as () => ConnectionColumn[] })
  readonly fields!: [ConnectionColumn, ConnectionColumn];
  @Prop({ type: String, default: "" })
  readonly query!: string;

  private counts: CountModel[] = [];

  created(): void {
    this.onChanged();
  }

  get option(): EChartsOption {
    const firstKeys = this.counts
      .map((count) => count.names[0])
      .filter(unique)
      .sort();
    const secondKeys = this.counts
      .map((count) => count.names[1])
      .filter(unique)
      .sort();
    return {
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "shadow",
        },
      },
      legend: {},
      xAxis: {
        type: "category",
        data: firstKeys,
      },
      yAxis: {
        type: "value",
      },
      series: secondKeys.map((secondKey) => {
        return {
          name: secondKey,
          type: "bar",
          stack: this.fields[1],
          emphasis: {
            focus: "series",
          },
          data: firstKeys.map(
            (firstKey) =>
              this.counts.find((count) =>
                isEqual(count.names, [firstKey, secondKey])
              )?.value ?? 0
          ),
        };
      }),
    };
  }

  @Watch("fields")
  @Watch("query")
  onChanged(): void {
    this.$connectionsApi
      .getCountsConnectionsCountsGet(this.fields, this.query)
      .then((response) => response.data)
      .then((counts) => {
        this.counts = counts;
      });
  }

  onClick(params: CallbackDataParams): void {
    this.$set(this.fieldSearches, this.fields[0], params.name);
    this.$set(this.fieldSearches, this.fields[1], params.seriesName);
  }
}
</script>
