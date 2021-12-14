<template>
  <div>
    <v-chart
      autoresize
      :option="option"
      :update-options="updateOptions"
      @click="onClick"
    ></v-chart>
    <range-slider
      v-if="hasSlider"
      :color="color"
      :get-range="getRange"
      @change="onSliderChange"
    ></range-slider>
  </div>
</template>

<style scoped>
.echarts {
  min-height: 256px;
}
</style>

<script lang="ts">
import {
  ConnectionField,
  ConnectionNumberField,
  CountModel,
  RangeModel,
} from "@/backend";
import RangeSlider from "@/components/commons/RangeSlider.vue";
import { Searches, sum } from "@/utils/common";
import { getColorPalette } from "@/utils/vuetify";
import { AxiosResponse } from "axios";
import { BarChart } from "echarts/charts";
import {
  LegendComponent,
  TitleComponent,
  TooltipComponent,
} from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  CallbackDataParams,
  EChartsOption,
  SetOptionOpts,
} from "echarts/types/dist/shared";
import _ from "lodash";
import VChart from "vue-echarts";
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import colors, { Color } from "vuetify/lib/util/colors";

use([
  CanvasRenderer,
  BarChart,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
]);

@Component({
  components: {
    VChart,
    RangeSlider,
  },
})
export default class ConnectionDoubleChart extends Vue {
  readonly updateOptions: SetOptionOpts = {
    notMerge: true,
  };

  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  fieldSearches!: Searches;
  @Prop({ type: Array as () => ConnectionField[] })
  readonly fields!: [ConnectionField, ConnectionField];
  @Prop({ type: String, default: "" })
  readonly query!: string;
  @Prop({ type: String, default: "bar" })
  readonly type!: "bar" | "line";
  @Prop({ type: Object as () => Color, default: () => colors.blue })
  readonly color!: Color;

  private counts: CountModel[] = [];

  created(): void {
    this.onChanged();
  }

  get defaultValue(): string | number {
    if (this.type === "line") {
      return 0;
    } else {
      return "";
    }
  }

  get option(): EChartsOption {
    const firstKeys: string[] = _(this.counts)
      .map((count) => count.names[0])
      .uniq()
      .sort()
      .value();
    const secondKeys: string[] = _(this.counts)
      .groupBy((count) => count.names[1])
      .map((values, key) => ({
        key: key,
        value: values.map((count) => count.value).reduce(sum),
      }))
      .sortBy(
        (item) => -item.value,
        (item) => item.key
      )
      .map((item) => item.key)
      .value();
    return {
      title: {
        text: this.$t("connection." + this.fields[1]).toString(),
        textStyle: {
          fontSize: 12,
          fontWeight: "normal",
        },
      },
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: this.type === "bar" ? "shadow" : undefined,
        },
      },
      legend: {
        right: 0,
      },
      xAxis: {
        type: "category",
        name: this.$t("connection." + this.fields[0]).toString(),
        nameLocation: "middle",
        nameGap: 28,
        boundaryGap: this.type === "bar",
        axisLabel: {
          formatter: (value: string) => {
            const n = Number(value);
            if (isNaN(n)) {
              return value;
            } else {
              return Math.round(n).toString();
            }
          },
        },
        data: firstKeys,
      },
      yAxis: {
        type: "value",
        name: "#",
        minInterval: 1,
      },
      series: secondKeys.map((secondKey) => {
        return {
          name: secondKey,
          type: this.type,
          stack: this.fields[1],
          areaStyle: {},
          emphasis: {
            focus: "series",
          },
          data: firstKeys.map(
            (firstKey) =>
              this.counts.find((count) =>
                _.isEqual(count.names, [firstKey, secondKey])
              )?.value ?? this.defaultValue
          ),
        };
      }),
      color: getColorPalette(this.color, secondKeys.length),
    };
  }

  get numberField(): ConnectionNumberField | undefined {
    const fieldString = this.fields[0].toString();
    return Object.values(ConnectionNumberField).find(
      (numberField) => fieldString === numberField.toString()
    );
  }

  get hasSlider(): boolean {
    return this.numberField !== undefined;
  }

  get getRange(): Promise<AxiosResponse<RangeModel>> | undefined {
    if (this.numberField) {
      return this.$connectionsApi.getRange(this.numberField);
    } else {
      return undefined;
    }
  }

  onSliderChange(value: [number, number]): void {
    this.$set(this.fieldSearches, this.fields[0], `${value[0]}<<${value[1]}`);
  }

  @Watch("fields")
  @Watch("query")
  onChanged(): void {
    this.$connectionsApi
      .getCounts(this.fields, this.query)
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
