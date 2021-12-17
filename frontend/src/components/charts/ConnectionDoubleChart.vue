<template>
  <div>
    <v-chart
      autoresize
      :option="option"
      :update-options="updateOptions"
      @click="onClick"
    ></v-chart>
    <range-slider
      v-if="isHistogram"
      v-model="range"
      :color="color"
      :get-range="getRange"
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
import { Bin, toBins } from "@/utils/statistics";
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
  @Prop({ type: Number, default: 10 })
  readonly stepCount!: number;

  private counts: CountModel[] = [];
  private range: [number, number] | null = null;

  created(): void {
    this.onChanged();
    this.$watch(`fieldSearches.${this.fields[0]}`, this.onFirstFieldChanged);
  }

  get stepSize(): number | undefined {
    if (this.isHistogram && this.firstKeys.length > 0) {
      return Math.ceil(
        (Number(this.firstKeys[this.firstKeys.length - 1]) -
          Number(this.firstKeys[0])) /
          this.stepCount
      );
    } else {
      return undefined;
    }
  }

  get defaultValue(): string | number {
    if (this.type === "line") {
      return 0;
    } else {
      return "";
    }
  }

  get firstKeys(): string[] {
    return _(this.counts)
      .map((count) => count.names[0])
      .uniq()
      .sort()
      .value();
  }

  get option(): EChartsOption {
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
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: this.type === "bar" ? "shadow" : undefined,
        },
      },
      legend: {
        tooltip: {
          show: true,
          formatter:
            this.$t("connection." + this.fields[1]).toString() + ": {a}",
        },
      },
      xAxis: {
        type: "category",
        name: this.$t("connection." + this.fields[0]).toString(),
        nameLocation: "middle",
        nameGap: 28,
        boundaryGap: this.type === "bar",
        data: this.isHistogram ? undefined : this.firstKeys,
        scale: true,
        axisTick: {
          alignWithLabel: true,
        },
      },
      yAxis: {
        type: "value",
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
          data: this.getData(secondKey),
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

  get isHistogram(): boolean {
    return this.numberField !== undefined;
  }

  get getRange(): Promise<AxiosResponse<RangeModel>> | undefined {
    if (this.numberField) {
      return this.$connectionsApi.getRange(this.numberField);
    } else {
      return undefined;
    }
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

  @Watch("range")
  onSliderChanged(value: [number, number] | null): void {
    if (value) {
      this.$set(this.fieldSearches, this.fields[0], `${value[0]}<<${value[1]}`);
    }
  }

  onFirstFieldChanged(value: string): void {
    if (value === undefined) {
      this.range = null;
    } else if (value.includes("<<")) {
      const [min, max] = value.split("<<", 2).map((v) => Number(v));
      if (min !== undefined && max !== undefined) {
        this.range = [min, max];
      }
    }
  }

  private getData(secondKey: string) {
    if (this.isHistogram) {
      const binData = this.firstKeys.map((firstKey) => ({
        value: Number(firstKey),
        count: this.getCount(firstKey, secondKey) ?? 0,
      }));
      return toBins(binData, this.stepSize);
    } else {
      return this.firstKeys.map(
        (firstKey) => this.getCount(firstKey, secondKey) ?? this.defaultValue
      );
    }
  }

  private getCount(firstKey: string, secondKey: string): number | undefined {
    return this.counts.find((c) => _.isEqual(c.names, [firstKey, secondKey]))
      ?.value;
  }

  onClick(params: CallbackDataParams): void {
    if (this.isHistogram) {
      const data = params.data as Bin;
      this.$set(this.fieldSearches, this.fields[0], `${data[2]}<<${data[3]}`);
    } else {
      this.$set(this.fieldSearches, this.fields[0], params.name);
    }
    this.$set(this.fieldSearches, this.fields[1], params.seriesName);
  }
}
</script>
