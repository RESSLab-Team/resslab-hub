<template>
  <div>
    <v-responsive min-height="100">
      <v-chart
        autoresize
        :init-options="initOptions"
        :option="option"
        :update-options="updateOptions"
        @click="click"
        @mouseover="mouseover"
        @mouseout="mouseout"
      />
    </v-responsive>
    <slot />
  </div>
</template>

<script lang="ts">
import { CountModel } from "@/backend";
import { initOptions, updateOptions } from "@/components/commons/charts/utils";
import { Searches } from "@/utils/common";
import { getColorPalette, primaryColor } from "@/utils/vuetify";
import { AxiosResponse } from "axios";
import { EChartsOption } from "echarts";
import { TreemapChart } from "echarts/charts";
import { TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { CallbackDataParams } from "echarts/types/dist/shared";
import VChart from "vue-echarts";
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

use([SVGRenderer, TreemapChart, TooltipComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class SingleChart extends Vue {
  readonly initOptions = initOptions;
  readonly updateOptions = updateOptions;

  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  fieldSearches!: Searches;
  @Prop({ type: String, default: "" })
  readonly labelPrefix!: string;
  @Prop({ type: String })
  readonly field!: string;
  @Prop({ type: String, default: "" })
  readonly query!: string;
  @Prop({ type: Object as () => Color, default: () => primaryColor })
  readonly color!: Color;
  @Prop({ type: Promise })
  readonly promise!: Promise<AxiosResponse<CountModel[]>>;

  private counts: Count[] = [];

  created(): void {
    this.onChanged();
  }

  get option(): EChartsOption {
    return {
      tooltip: {
        trigger: "item",
        confine: true,
      },
      series: [
        {
          type: "treemap",
          id: this.field,
          name: this.$t(this.labelPrefix + this.field).toString(),
          left: 0,
          top: 0,
          right: 0,
          bottom: 0,
          data: this.counts.map((count) => {
            return {
              name: count.name,
              value: count.value,
            };
          }),
          breadcrumb: {
            show: false,
          },
          roam: false,
        },
      ],
      color: getColorPalette(this.color, this.counts.length),
    };
  }

  @Watch("field")
  @Watch("query")
  onChanged(): void {
    this.promise
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

  click(params: CallbackDataParams): void {
    if (params.seriesId) {
      this.$set(this.fieldSearches, params.seriesId, params.name);
    }
  }

  mouseover(params: CallbackDataParams): void {
    this.$emit("mouseover", params);
  }

  mouseout(): void {
    this.$emit("mouseout");
  }
}

interface Count {
  name: string;
  value: number;
}
</script>
