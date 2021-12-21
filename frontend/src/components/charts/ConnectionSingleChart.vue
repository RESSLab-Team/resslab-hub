<template>
  <div>
    <v-chart
      autoresize
      :option="option"
      :update-options="updateOptions"
      @click="onClick"
      @mouseover="onMouseover"
      @mouseout="onMouseout"
    ></v-chart>
    <v-img v-if="imageUrl" contain :src="imageUrl" max-height="160"></v-img>
  </div>
</template>

<style scoped>
.echarts {
  min-height: 100px;
}
</style>

<script lang="ts">
import { ConnectionField } from "@/backend";
import { publicPath, Searches } from "@/utils/common";
import { getColorPalette } from "@/utils/vuetify";
import { TreemapChart } from "echarts/charts";
import { TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  CallbackDataParams,
  EChartsOption,
  SetOptionOpts,
} from "echarts/types/dist/shared";
import VChart from "vue-echarts";
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import colors, { Color } from "vuetify/lib/util/colors";

use([CanvasRenderer, TreemapChart, TooltipComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class ConnectionSingleChart extends Vue {
  readonly updateOptions: SetOptionOpts = {
    notMerge: true,
  };

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
      color: getColorPalette(this.color, this.counts.length),
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
      this.imageUrl = publicPath + "img/connection-type/" + name + ".png";
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
