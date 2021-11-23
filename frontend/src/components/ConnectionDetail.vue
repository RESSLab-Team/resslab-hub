<template>
  <v-row>
    <v-col v-if="globalSeries.length > 0" cols="6">
      <v-card>
        <v-card-title>Global</v-card-title>
        <v-chart :option="globalOption"></v-chart>
      </v-card>
    </v-col>
    <v-col v-if="panelZoneSeries.length > 0" cols="6">
      <v-card>
        <v-card-title>Panel Zone</v-card-title>
        <v-chart :option="panelZoneOption"></v-chart>
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

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class ConnectionDetail extends Vue {
  @Prop(String) readonly connectionId: string | undefined;
  globalSeries: number[][] = [];
  panelZoneSeries: number[][] = [];

  created(): void {
    this.onChanged();
  }

  get globalOption(): EChartsOption {
    return {
      xAxis: {
        name: "Total story drift angle (rad)",
        nameLocation: "middle",
        nameGap: 36,
      },
      yAxis: {
        name: "Force in the actuator (kN)",
        nameLocation: "middle",
        nameGap: 36,
      },
      tooltip: {
        trigger: "axis",
      },
      series: [
        {
          type: "line",
          data: this.globalSeries,
        },
      ],
    };
  }

  get panelZoneOption(): EChartsOption {
    return {
      xAxis: {
        name: "Panel zone shear distortion (rad)",
        nameLocation: "middle",
        nameGap: 36,
      },
      yAxis: {
        name: "Panel zone shear force (kN)",
        nameLocation: "middle",
        nameGap: 36,
      },
      tooltip: {
        trigger: "axis",
      },
      series: [
        {
          type: "line",
          data: this.panelZoneSeries,
        },
      ],
    };
  }

  @Watch("field")
  onChanged(): void {
    if (this.connectionId) {
      this.$connectionsApi
        .getGlobalsConnectionsConnectionIdGlobalsGet(this.connectionId)
        .then((response) => response.data)
        .then((series) => {
          this.globalSeries = series;
        });
      this.$connectionsApi
        .getPanelZonesConnectionsConnectionIdPanelZonesGet(this.connectionId)
        .then((response) => response.data)
        .then((series) => {
          this.panelZoneSeries = series;
        });
    }
  }
}
</script>
