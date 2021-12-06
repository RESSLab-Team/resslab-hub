<template>
  <div>
    <v-chart
      :option="option"
      @click="onClick"
      @mouseover="onMouseover"
      @mouseout="onMouseout"
    ></v-chart>
    <v-img v-if="imageUrl" contain :src="imageUrl" max-height="160"></v-img>
  </div>
</template>

<style scoped>
.echarts {
  min-height: 128px;
}
</style>

<script lang="ts">
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import VChart from "vue-echarts";
import { ConnectionField } from "@/backend";
import { use } from "echarts/core";
import { TreemapChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { TooltipComponent } from "echarts/components";
import { EChartsOption, CallbackDataParams } from "echarts/types/dist/shared";
import { Searches } from "@/utils/common";
import colors, { Color } from "vuetify/lib/util/colors";
import { getColorPalette } from "@/utils/vuetify";

use([CanvasRenderer, TreemapChart, TooltipComponent]);

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
  @Prop({ type: Object as () => Color, default: () => colors.blue })
  readonly color!: Color;

  private counts: Count[] = [];
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
          type: "treemap",
          id: this.field,
          name: this.$t("connection." + this.field).toString(),
          data: this.counts.map((count) => {
            return {
              name: count.name,
              value: count.value,
            };
          }),
          breadcrumb: {
            show: false,
          },
          roam: "move",
        },
      ],
      color: getColorPalette(this.color),
    };
  }

  @Watch("field")
  @Watch("query")
  onChanged(): void {
    this.$connectionsApi
      .getCounts([this.field], this.query)
      .then((response) => response.data)
      .then((counts) => {
        this.counts = counts
          .map((count) => {
            return {
              name: count.names[0],
              value: count.value,
            };
          })
          .sort((c1, c2) => (c1.name < c2.name ? -1 : 1));
      });
  }

  onClick(params: CallbackDataParams): void {
    if (params.seriesId) {
      this.$set(this.fieldSearches, params.seriesId, params.name);
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

interface Count {
  name: string;
  value: number;
}
</script>
