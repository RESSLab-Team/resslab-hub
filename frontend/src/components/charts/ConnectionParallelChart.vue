<template>
  <v-chart :option="option" @click="onClick"></v-chart>
</template>

<style scoped>
.echarts {
  min-height: 256px;
}
</style>

<script lang="ts">
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import VChart from "vue-echarts";
import { ConnectionField } from "@/backend";
import { use } from "echarts/core";
import { ParallelChart } from "echarts/charts";
import { CanvasRenderer } from "echarts/renderers";
import { EChartsOption, CallbackDataParams } from "echarts/types/dist/shared";
import { Searches, unique } from "@/utils/common";
import _ from "lodash";

use([CanvasRenderer, ParallelChart]);

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

  private ids: string[] = [];
  private data: (number | string)[][] = [];

  created(): void {
    this.onChanged();
  }

  get option(): EChartsOption {
    return {
      parallelAxis: this.fields.map((field, index) => {
        const name = this.$t("connection." + field).toString();
        const transposedData = _.zip(...this.data) as (string | number)[][];
        const values = transposedData[index] as (string | number)[] | undefined;
        if (values) {
          const type = typeof values[0];
          const sortedValues = values.filter(unique).sort();
          if (type === "number") {
            return {
              id: field,
              dim: index,
              name: name,
              type: "value",
              min: sortedValues[0],
              max: sortedValues[sortedValues.length - 1],
            };
          } else {
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

  onClick(params: CallbackDataParams): void {
    this.$set(
      this.fieldSearches,
      ConnectionField.Id,
      this.ids[params.dataIndex]
    );
  }
}
</script>
