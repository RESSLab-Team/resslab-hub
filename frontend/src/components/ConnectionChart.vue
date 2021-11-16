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

<script lang="ts">
import { Component, Vue, Watch } from "vue-property-decorator";
import VChart from "vue-echarts";
import { ConnectionColumn, CountModel } from "@/backend";
import { use } from "echarts/core";
import { PieChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { TooltipComponent } from "echarts/components";

use([CanvasRenderer, PieChart, TooltipComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class ConnectionChart extends Vue {
  fields: string[] = Object.values(ConnectionColumn);
  field = ConnectionColumn.ConnectionType;
  counts: CountModel[] = [];

  created(): void {
    this.onChanged();
  }

  get option(): unknown {
    return {
      tooltip: {
        trigger: "item",
      },
      series: [
        {
          name: this.field,
          type: "pie",
          radius: ["40%", "80%"],
          data: this.counts,
        },
      ],
    };
  }

  @Watch("field")
  onChanged(): void {
    this.$connectionsApi
      .countConnectionsCountGet(this.field)
      .then((response) => response.data)
      .then((counts) => {
        this.counts = counts;
      });
  }
}
</script>
