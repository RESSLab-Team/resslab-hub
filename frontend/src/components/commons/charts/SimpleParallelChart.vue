<template>
  <v-card>
    <v-card-title>
      <slot name="title"></slot>
    </v-card-title>
    <v-responsive :aspect-ratio="fields.length / 2" min-height="150">
      <v-chart
        ref="chart"
        autoresize
        :option="option"
        @click="onClick"
        @brushselected="onBrush"
      ></v-chart>
    </v-responsive>
    <v-card-actions>
      <v-btn
        color="primary"
        :disabled="selectedIds.length === 0"
        text
        @click="onApply"
      >
        <v-icon left>mdi-filter-variant</v-icon>
        Apply selection ({{ selectedIds.length }})
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script lang="ts">
import { MatrixModel } from "@/backend";
import { Searches } from "@/utils/common";
import { primaryColor } from "@/utils/vuetify";
import { AxiosResponse } from "axios";
import { ParallelChart } from "echarts/charts";
import { BrushComponent, ToolboxComponent } from "echarts/components";
import { ECharts, use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  CallbackDataParams,
  EChartsOption,
  Payload,
} from "echarts/types/dist/shared";
import _ from "lodash";
import VChart from "vue-echarts";
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

use([CanvasRenderer, ParallelChart, BrushComponent, ToolboxComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class SimpleParallelChart extends Vue {
  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  fieldSearches!: Searches;
  @Prop({ type: String, default: "" })
  readonly labelPrefix!: string;
  @Prop({ type: Array as () => ParallelField[] })
  readonly fields!: ParallelField[];
  @Prop({ type: String, default: "" })
  readonly query!: string;
  @Prop({ type: Object as () => Color, default: () => primaryColor })
  readonly color!: Color;
  @Prop({ type: String })
  readonly idField!: string;
  @Prop({ type: Function })
  readonly getMatrix!: (
    fields: string[]
  ) => Promise<AxiosResponse<MatrixModel>>;

  private ids: string[] = [];
  private data: (number | string)[][] = [];
  private selectedIds: string[] = [];

  private unwatch: () => void = () => null;

  created(): void {
    this.onChanged();
    this.unwatch = this.$watch(
      `fieldSearches.${this.idField}`,
      this.onSearchChanged
    );
  }

  beforeDestroy(): void {
    this.unwatch();
  }

  get chart(): ECharts | undefined {
    return this.$refs.chart as ECharts | undefined;
  }

  get transposedData(): (string | number)[][] {
    return _.zip(...this.data) as (string | number)[][];
  }

  get requestFields(): string[] {
    return _(this.fields)
      .flatMap((f) => {
        if (typeof f === "string") {
          return [f];
        } else {
          return [f.dividend, f.divisor];
        }
      })
      .uniq()
      .value();
  }

  get option(): EChartsOption {
    return {
      brush: {
        brushLink: "all",
        toolbox: ["clear"],
      },
      parallel: {
        left: 80,
        top: 34,
        right: 80,
        bottom: 8,
      },
      parallelAxis: this.fields.map((field, index) => {
        const id: string =
          typeof field === "string"
            ? field
            : `${field.dividend}/${field.divisor}`;
        const name = this.$t(this.labelPrefix + id).toString();
        const values = this.getValues(field);
        if (values) {
          const type = typeof values[0];
          if (type === "number") {
            return {
              id: id,
              dim: index,
              name: name,
              type: "value",
              scale: true,
            };
          } else {
            const sortedValues = _(values).uniq().sort().value();
            return {
              id: id,
              dim: index,
              name: name,
              nameLocation: "start",
              inverse: true,
              type: "category",
              axisTick: {
                alignWithLabel: true,
              },
              data: sortedValues,
            };
          }
        } else {
          return {
            id: id,
            dim: index,
            name: name,
          };
        }
      }),
      series: {
        type: "parallel",
        data: this.data.map((d) =>
          this.fields.map((f) => {
            if (typeof f === "string") {
              return d[this.requestFields.indexOf(f)];
            } else {
              return (
                (d[this.requestFields.indexOf(f.dividend)] as number) /
                (d[this.requestFields.indexOf(f.divisor)] as number)
              );
            }
          })
        ),
        emphasis: {
          focus: "series",
          lineStyle: {
            width: 6,
          },
        },
      },
      color: this.color.base,
    };
  }

  @Watch("fields")
  @Watch("query")
  onChanged(): void {
    this.getMatrix(this.requestFields)
      .then((response) => response.data)
      .then((matrixModel) => {
        this.ids = matrixModel.ids;
        this.data = matrixModel.data;
      });
  }

  private getValues(field: ParallelField): (string | number)[] {
    if (typeof field === "string") {
      return this.transposedData[this.requestFields.indexOf(field)];
    } else {
      return _.zip(
        this.transposedData[this.requestFields.indexOf(field.dividend)],
        this.transposedData[this.requestFields.indexOf(field.divisor)]
      )
        .map((v) => v as [number, number])
        .map((v) => v[0] / v[1]);
    }
  }

  onSearchChanged(value: string | undefined): void {
    if (value === undefined) {
      this.clear();
    }
  }

  onClick(params: CallbackDataParams): void {
    this.$set(this.fieldSearches, this.idField, this.ids[params.dataIndex]);
  }

  onBrush(payload: Payload): void {
    const selectedIndexes: number[] =
      payload.batch?.pop()?.selected?.pop()?.dataIndex ?? [];
    if (selectedIndexes.length > 0) {
      this.selectedIds = selectedIndexes.map((index) => this.ids[index]);
    }
  }

  onApply(): void {
    this.$set(this.fieldSearches, this.idField, this.selectedIds.join(","));
    this.clear();
  }

  clear(): void {
    this.chart?.clear();
    this.selectedIds = [];
  }
}

export type ParallelField<T = string> = T | Division<T>;

export interface Division<T> {
  dividend: T;
  divisor: T;
}
</script>
