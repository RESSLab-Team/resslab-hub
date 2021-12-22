<template>
  <div>
    <v-responsive aspect-ratio="5" min-height="256">
      <v-chart
        ref="chart"
        autoresize
        :option="option"
        @click="onClick"
        @brushselected="onBrush"
      ></v-chart>
    </v-responsive>
    <v-btn
      color="primary"
      :disabled="selectedIds.length === 0"
      text
      @click="onApply"
    >
      <v-icon left>mdi-filter-variant</v-icon>
      Apply selection ({{ selectedIds.length }})
    </v-btn>
  </div>
</template>

<script lang="ts">
import { ConnectionField } from "@/backend";
import { Searches } from "@/utils/common";
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
import colors, { Color } from "vuetify/lib/util/colors";

use([CanvasRenderer, ParallelChart, BrushComponent, ToolboxComponent]);

@Component({
  components: {
    VChart,
  },
})
export default class ConnectionParallelChart extends Vue {
  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  fieldSearches!: Searches;
  @Prop({ type: Array as () => ConnectionField[] })
  readonly fields!: ConnectionField[];
  @Prop({ type: String, default: "" })
  readonly query!: string;
  @Prop({ type: Object as () => Color, default: () => colors.blue })
  readonly color!: Color;

  private ids: string[] = [];
  private data: (number | string)[][] = [];
  private selectedIds: string[] = [];

  created(): void {
    this.onChanged();
  }

  get chart(): ECharts | undefined {
    return this.$refs.chart as ECharts | undefined;
  }

  get option(): EChartsOption {
    return {
      brush: {
        brushLink: "all",
        toolbox: ["clear"],
      },
      parallelAxis: this.fields.map((field, index) => {
        const name = this.$t("connection." + field).toString();
        const transposedData = _.zip(...this.data) as (string | number)[][];
        const values = transposedData[index] as (string | number)[] | undefined;
        if (values) {
          const type = typeof values[0];
          if (type === "number") {
            return {
              id: field,
              dim: index,
              name: name,
              type: "value",
              scale: true,
            };
          } else {
            const sortedValues = _(values).uniq().sort().value();
            return {
              id: field,
              dim: index,
              name: name,
              nameLocation: "start",
              inverse: true,
              type: "category",
              data: sortedValues,
            };
          }
        } else {
          return {
            id: field,
            dim: index,
            name: name,
          };
        }
      }),
      series: {
        type: "parallel",
        data: this.data,
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
    this.$connectionsApi
      .getMatrix(this.fields, this.query)
      .then((response) => response.data)
      .then((matrixModel) => {
        this.ids = matrixModel.ids;
        this.data = matrixModel.data;
      });
  }

  @Watch(`fieldSearches.${ConnectionField.Id}`)
  onSearchChanged(value: string | undefined): void {
    if (value === undefined) {
      this.clear();
    }
  }

  onClick(params: CallbackDataParams): void {
    this.$set(
      this.fieldSearches,
      ConnectionField.Id,
      this.ids[params.dataIndex]
    );
  }

  onBrush(payload: Payload): void {
    const selectedIndexes: number[] =
      payload.batch?.pop()?.selected?.pop()?.dataIndex ?? [];
    if (selectedIndexes.length > 0) {
      this.selectedIds = selectedIndexes.map((index) => this.ids[index]);
    }
  }

  onApply(): void {
    this.$set(
      this.fieldSearches,
      ConnectionField.Id,
      this.selectedIds.join(",")
    );
    this.clear();
  }

  clear(): void {
    this.chart?.clear();
    this.selectedIds = [];
  }
}
</script>
