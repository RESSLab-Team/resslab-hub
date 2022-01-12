<template>
  <div>
    <v-responsive aspect-ratio="2.5" min-height="200">
      <v-chart
        autoresize
        :option="option"
        :update-options="updateOptions"
        @click="click"
      ></v-chart>
    </v-responsive>
    <range-slider
      v-if="isHistogram"
      v-model="range"
      :color="color"
      :get-range="rangePromise"
    ></range-slider>
  </div>
</template>

<script lang="ts">
import { CountModel, RangeModel } from "@/backend";
import RangeSlider from "@/components/commons/sliders/RangeSlider.vue";
import { Searches, sum } from "@/utils/common";
import { BinData, toBins } from "@/utils/statistics";
import { getColorPalette, primaryColor } from "@/utils/vuetify";
import { AxiosResponse } from "axios";
import { BarChart, LineChart } from "echarts/charts";
import {
  GridComponent,
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
import { Color } from "vuetify/lib/util/colors";

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  GridComponent,
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
export default class DoubleChart extends Vue {
  readonly updateOptions: SetOptionOpts = {
    notMerge: true,
  };

  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  fieldSearches!: Searches;
  @Prop({ type: Array as () => (string | DoubleField)[] })
  readonly fields!: [string, DoubleField];
  @Prop({ type: String, default: "" })
  readonly query!: string;
  @Prop({ type: String, default: "bar" })
  readonly type!: "bar" | "line";
  @Prop({ type: Object as () => Color, default: () => primaryColor })
  readonly color!: Color;
  @Prop({ type: String, default: "" })
  readonly labelPrefix!: string;
  @Prop({ type: String })
  readonly numberField: string | undefined;
  @Prop({ type: Promise })
  readonly promise!: Promise<AxiosResponse<CountModel[]>>;
  @Prop({ type: Promise })
  readonly rangePromise: Promise<AxiosResponse<RangeModel>> | undefined;

  counts: CountModel[] = [];
  range: [number, number] | null = null;
  private unwatch: () => void = () => null;

  created(): void {
    this.onChanged();
    this.unwatch = this.$watch(
      `fieldSearches.${this.fields[0]}`,
      this.onFirstFieldChanged
    );
  }

  beforeDestroy(): void {
    this.unwatch();
  }

  get defaultValue(): string | number {
    if (this.type === "line") {
      return 0;
    } else {
      return "";
    }
  }

  get secondField(): string {
    const secondField: DoubleField = this.fields[1];
    if (typeof secondField === "string") {
      return secondField;
    } else {
      return secondField.id;
    }
  }

  get mapSecondName(): (name: string) => string {
    const secondField: DoubleField = this.fields[1];
    if (typeof secondField === "string") {
      return (name) => name;
    } else {
      return (name) => secondField.mapping.get(name) ?? name;
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
      title: {
        text: this.$t(this.labelPrefix + this.secondField).toString(),
        textStyle: {
          fontSize: 12,
        },
        left: "center",
      },
      legend: {
        type: "scroll",
        top: 20,
      },
      grid: {
        bottom: 42,
      },
      xAxis: {
        type: "category",
        name: this.$t(this.labelPrefix + this.fields[0]).toString(),
        nameLocation: "middle",
        nameTextStyle: {
          fontWeight: "bold",
        },
        nameGap: 28,
        boundaryGap: this.type === "bar",
        scale: true,
        axisTick: {
          alignWithLabel: true,
        },
      },
      yAxis: {
        type: "value",
        minInterval: 1,
      },
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: this.type === "bar" ? "shadow" : undefined,
        },
        confine: true,
      },
      series: this.getSerie(secondKeys).map((serie) => ({
        id: serie.name,
        name: this.mapSecondName(serie.name),
        type: this.type,
        showSymbol: false,
        stack: this.secondField,
        areaStyle: {},
        emphasis: {
          focus: "series",
        },
        data: serie.data,
      })),
      color: getColorPalette(this.color, secondKeys.length),
    };
  }

  get isHistogram(): boolean {
    return this.numberField !== undefined;
  }

  @Watch("fields")
  @Watch("query")
  onChanged(): void {
    this.promise
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

  private getSerie(secondKeys: string[]): Serie[] {
    if (this.isHistogram) {
      if (this.type === "line") {
        return secondKeys.map((secondKey) => {
          const firstKeyNumbers = this.firstKeys.map((firstKey) =>
            Number(firstKey)
          );
          let acc = 0;
          const values: [number, number][] = _.range(
            Math.min(...firstKeyNumbers),
            Math.max(...firstKeyNumbers) + 1
          ).map((firstKeyNumber) => {
            const count = (acc +=
              this.getCount(firstKeyNumber.toString(), secondKey) ?? 0);
            return [firstKeyNumber, count];
          });
          return {
            name: secondKey,
            data: values,
          };
        });
      } else {
        const binData = this.firstKeys.flatMap((firstKey) =>
          secondKeys.map((secondKey) => ({
            name: secondKey,
            value: Number(firstKey),
            count: this.getCount(firstKey, secondKey) ?? 0,
          }))
        );
        return toBins(secondKeys, binData);
      }
    } else {
      return secondKeys.map((secondKey) => ({
        name: secondKey,
        data: this.firstKeys.map((firstKey) => [
          firstKey,
          this.getCount(firstKey, secondKey) ?? this.defaultValue,
        ]),
      }));
    }
  }

  private getCount(firstKey: string, secondKey: string): number | undefined {
    return this.counts.find((c) => _.isEqual(c.names, [firstKey, secondKey]))
      ?.value;
  }

  click(params: CallbackDataParams): void {
    if (this.type === "bar") {
      if (this.isHistogram) {
        const data = params.data as BinData;
        this.$set(this.fieldSearches, this.fields[0], `${data[2]}<<${data[3]}`);
      } else {
        this.$set(this.fieldSearches, this.fields[0], params.name);
      }
    }
    this.$set(this.fieldSearches, this.secondField, params.seriesId);
  }
}

export type DoubleField<T = string> = T | MappingField<T>;

export interface MappingField<T> {
  id: T;
  mapping: Map<string, string>;
}

interface Serie {
  name: string;
  data: (string | number)[][];
}
</script>
