<template>
  <v-card>
    <v-card-text>
      <locale-select
        v-model="singleField"
        :items="fields"
        prefix="connection."
      ></locale-select>
      <v-chart :option="singleOption" @click="onClick"></v-chart>
    </v-card-text>
    <v-divider></v-divider>
    <v-card-text>
      <locale-select
        v-model="doubleField[0]"
        :items="fields"
        prefix="connection."
      ></locale-select>
      <locale-select
        v-model="doubleField[1]"
        :items="fields"
        prefix="connection."
      ></locale-select>
      <v-chart
        :option="doubleOption"
        :update-options="updateOptions"
        @click="onClick"
      ></v-chart>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.echarts {
  min-height: 256px;
}
</style>
<style>
img.tooltip {
  max-height: 256px;
  max-width: 256px;
}
</style>

<script lang="ts">
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import VChart from "vue-echarts";
import { ConnectionColumn, CountModel } from "@/backend";
import { use } from "echarts/core";
import { BarChart, PieChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { LegendComponent, TooltipComponent } from "echarts/components";
import {
  EChartsOption,
  CallbackDataParams,
  SetOptionOpts,
} from "echarts/types/dist/shared";
import { Searches, unique } from "@/utils/common";
import { isEqual } from "lodash";
import LocaleSelect from "@/components/commons/LocaleSelect.vue";

use([CanvasRenderer, BarChart, PieChart, LegendComponent, TooltipComponent]);

@Component({
  components: {
    LocaleSelect,
    VChart,
  },
})
export default class ConnectionChart extends Vue {
  readonly publicPath: string = process.env.BASE_URL;
  readonly fields: string[] = Object.values(ConnectionColumn);
  readonly connectionTypes = new Set([
    "beep",
    "bfp",
    "kbb",
    "rbs",
    "wfp",
    "wuf-b",
    "wuf-w",
  ]);
  readonly updateOptions: SetOptionOpts = {
    notMerge: true,
  };

  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  fieldSearches!: Searches;
  @Prop({ default: "" })
  readonly query!: string;

  singleField = ConnectionColumn.ConnectionType;
  singleCounts: CountModel[] = [];
  doubleField: [ConnectionColumn, ConnectionColumn] = [
    ConnectionColumn.DC,
    ConnectionColumn.NDp,
  ];
  doubleCounts: CountModel[] = [];

  created(): void {
    this.onChangedSingle();
    this.onChangedDouble();
  }

  get singleOption(): EChartsOption {
    return {
      tooltip: {
        trigger: "item",
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter: (params: any) => {
          const name: string = params.name;
          const value: string = params.value;
          const percent: number = params.percent;
          const defaultFormat = `${name}: <strong>${value}</strong> (${percent}%)`;
          if (this.connectionTypes.has(name.toLowerCase())) {
            const src =
              this.publicPath +
              "img/connection-type/" +
              name.toLowerCase() +
              ".png";
            return `<img class="tooltip" src="${src}"></img>
            <div>${defaultFormat}</div>`;
          } else {
            return defaultFormat;
          }
        },
      },
      series: [
        {
          type: "pie",
          name: this.singleField,
          data: this.singleCounts.map((count) => {
            return {
              name: count.names[0],
              value: count.value,
            };
          }),
          radius: ["40%", "80%"],
        },
      ],
    };
  }

  get doubleOption(): EChartsOption {
    const firstKeys = this.doubleCounts
      .map((count) => count.names[0])
      .filter(unique)
      .sort();
    const secondKeys = this.doubleCounts
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
          stack: this.doubleField[1],
          emphasis: {
            focus: "series",
          },
          data: firstKeys.map(
            (firstKey) =>
              this.doubleCounts.find((count) =>
                isEqual(count.names, [firstKey, secondKey])
              )?.value ?? 0
          ),
        };
      }),
    };
  }

  @Watch("singleField")
  @Watch("query")
  onChangedSingle(): void {
    this.$connectionsApi
      .getCountsConnectionsCountsGet([this.singleField], this.query)
      .then((response) => response.data)
      .then((counts) => {
        this.singleCounts = counts;
      });
  }

  @Watch("doubleField")
  @Watch("query")
  onChangedDouble(): void {
    this.$connectionsApi
      .getCountsConnectionsCountsGet(this.doubleField, this.query)
      .then((response) => response.data)
      .then((counts) => {
        this.doubleCounts = counts;
      });
  }

  onClick(params: CallbackDataParams): void {
    if (params.seriesName) {
      this.$set(this.fieldSearches, params.seriesName, params.name);
    }
  }
}
</script>
