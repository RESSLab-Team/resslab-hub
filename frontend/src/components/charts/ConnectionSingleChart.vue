<template>
  <div>
    <v-chart
      :option="option"
      @click="onClick"
      @mouseover="onMouseover"
      @mouseout="onMouseout"
    ></v-chart>
    <v-img v-if="imageUrl" :src="imageUrl"></v-img>
  </div>
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
import { ConnectionField, CountModel } from "@/backend";
import { use } from "echarts/core";
import { PieChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { TooltipComponent } from "echarts/components";
import { EChartsOption, CallbackDataParams } from "echarts/types/dist/shared";
import { Searches } from "@/utils/common";

use([CanvasRenderer, PieChart, TooltipComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class ConnectionSingleChart extends Vue {
  readonly publicPath: string = process.env.BASE_URL;

  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  fieldSearches!: Searches;
  @Prop({ type: String as () => ConnectionField })
  readonly field!: ConnectionField;
  @Prop({ type: String, default: "" })
  readonly query!: string;

  private counts: CountModel[] = [];
  imageUrl = "";

  created(): void {
    this.onChanged();
  }

  get option(): EChartsOption {
    return {
      tooltip: {
        trigger: "item",
      },
      series: [
        {
          type: "pie",
          name: this.$t("connection." + this.field).toString(),
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
  @Watch("query")
  onChanged(): void {
    this.$connectionsApi
      .getCountsConnectionsCountsGet([this.field], this.query)
      .then((response) => response.data)
      .then((counts) => {
        this.counts = counts;
      });
  }

  onClick(params: CallbackDataParams): void {
    if (params.seriesName) {
      this.$set(this.fieldSearches, params.seriesName, params.name);
    }
  }

  onMouseover(params: CallbackDataParams): void {
    if (this.field === ConnectionField.ConnectionType) {
      const name: string = params.name.toLowerCase();
      this.imageUrl = this.publicPath + "img/connection-type/" + name + ".png";
    }
  }

  onMouseout(): void {
    this.imageUrl = "";
  }
}
</script>
