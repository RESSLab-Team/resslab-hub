<template>
  <v-row>
    <v-col>
      <v-card>
        <v-card-title>Global</v-card-title>
        <v-chart :option="option"></v-chart>
      </v-card>
    </v-col>
  </v-row>
</template>

<style scoped>
.echarts {
  min-height: 512px;
}
</style>

<script lang="ts">
import { Component, Vue, Watch, Prop } from "vue-property-decorator";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { GridComponent, TooltipComponent } from "echarts/components";
import { EChartsOption } from "echarts/types/dist/shared";
import { SerieModel } from "@/backend";

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class ConnectionDetail extends Vue {
  @Prop(String) readonly connectionId: string | undefined;
  series: SerieModel[] = [];

  created(): void {
    this.onChanged();
  }

  get option(): EChartsOption {
    return {
      xAxis: {
        name: "Total story drift angle (rad)",
        nameRotate: 90,
      },
      yAxis: {
        name: "Force in the actuator (kN)",
      },
      tooltip: {
        trigger: "axis",
      },
      series: [
        {
          type: "line",
          data: this.series.map((serie) => [serie.x, serie.y]),
        },
      ],
    };
  }

  @Watch("field")
  onChanged(): void {
    if (this.connectionId) {
      this.$connectionsApi
        .getSeriesConnectionsConnectionIdGlobalsGet(this.connectionId)
        .then((response) => response.data)
        .then((series) => {
          this.series = series;
        });
    }
  }
}
</script>
