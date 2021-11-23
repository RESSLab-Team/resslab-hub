<template>
  <v-card>
    <v-card-title>
      <v-select v-model="field" :items="fields"></v-select>
    </v-card-title>
    <v-chart :option="option"></v-chart>
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
import { Component, Vue, Watch } from "vue-property-decorator";
import VChart from "vue-echarts";
import { ConnectionColumn, CountModel } from "@/backend";
import { use } from "echarts/core";
import { PieChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { TooltipComponent } from "echarts/components";
import { EChartsOption } from "echarts/types/dist/shared";

use([CanvasRenderer, PieChart, TooltipComponent]);

@Component({
  components: {
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

  field = ConnectionColumn.ConnectionType;
  counts: CountModel[] = [];

  created(): void {
    this.onChanged();
  }

  get option(): EChartsOption {
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
          name: this.field,
          data: this.counts.map((count) => {
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

  @Watch("field")
  onChanged(): void {
    this.$connectionsApi
      .getCountsConnectionsCountsGet([this.field])
      .then((response) => response.data)
      .then((counts) => {
        this.counts = counts;
      });
  }
}
</script>
