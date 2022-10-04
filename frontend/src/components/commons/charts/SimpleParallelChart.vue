<template>
  <v-card>
    <v-card-title>
      <slot name="title">
        Parallel View of all Tests
        <info-tooltip>
          <p>
            In this parallel coordinate plots, you can view all available tests
            in the database, ordered according to key variables. Each line
            represents a single test.
          </p>
          How to use?
          <ul>
            <li>
              Filter a subset of the data by selecting values on the vertical
              axis directly
            </li>
            <li>Select a specific test by clicking on the respective line.</li>
          </ul>
        </info-tooltip>
      </slot>
    </v-card-title>
    <v-responsive aspect-ratio="4" min-height="100">
      <v-chart
        ref="chart"
        autoresize
        :init-options="initOptions"
        :option="option"
        :update-options="updateOptions"
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
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import { Searches } from "@/utils/common";
import { VerticalAlign, ZRFontWeight } from "@/utils/echarts";
import { primaryColor } from "@/utils/vuetify";
import { AxiosResponse } from "axios";
import { EChartsOption, Payload } from "echarts";
import { ParallelChart } from "echarts/charts";
import { BrushComponent, ToolboxComponent } from "echarts/components";
import { ECharts, use } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { CallbackDataParams } from "echarts/types/dist/shared";
import { chain, merge, zip } from "lodash";
import VChart from "vue-echarts";
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";
import { initOptions, updateOptions } from "@/components/commons/charts/utils";

use([SVGRenderer, ParallelChart, BrushComponent, ToolboxComponent]);

@Component({
  components: {
    InfoTooltip,
    VChart,
  },
})
export default class SimpleParallelChart extends Vue {
  readonly initOptions = initOptions;
  readonly updateOptions = updateOptions;

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
    return zip(...this.data) as (string | number)[][];
  }

  get requestFields(): string[] {
    return chain(this.fields)
      .flatMap((f) => {
        if (typeof f.id === "string") {
          return [f.id];
        } else {
          return [f.id.dividend, f.id.divisor];
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
        left: 60,
        top: 40,
        right: 120,
        bottom: 8,
      },
      parallelAxis: this.fields.map((field, index) => {
        const id: string =
          typeof field.id === "string"
            ? field.id
            : `${field.id.dividend}/${field.id.divisor}`;
        const name = field.name ?? this.$t(this.labelPrefix + id).toString();
        const values = this.getValues(field);
        const option = {
          id: id,
          dim: index,
          name: name,
          nameTextStyle: {
            fontWeight: "bold" as ZRFontWeight,
            verticalAlign: "middle" as VerticalAlign,
          },
          nameGap: 20,
        };
        if (values) {
          const type = typeof values.find((v) => v != null);
          if (type === "number") {
            return merge(option, {
              type: "value",
              scale: true,
            });
          } else {
            const sortedValues = chain(values).uniq().sort().value();
            return merge(option, {
              nameLocation: "start",
              inverse: true,
              type: "category",
              axisTick: {
                alignWithLabel: true,
              },
              data: sortedValues,
            });
          }
        } else {
          return option;
        }
      }),
      series: {
        type: "parallel",
        data: this.data.map((d) =>
          this.fields.map((f) => {
            if (typeof f.id === "string") {
              return d[this.requestFields.indexOf(f.id)];
            } else {
              return (
                (d[this.requestFields.indexOf(f.id.dividend)] as number) /
                (d[this.requestFields.indexOf(f.id.divisor)] as number)
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
    if (typeof field.id === "string") {
      return this.transposedData[this.requestFields.indexOf(field.id)];
    } else {
      return zip(
        this.transposedData[this.requestFields.indexOf(field.id.dividend)],
        this.transposedData[this.requestFields.indexOf(field.id.divisor)]
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

export interface ParallelField<T = string> {
  id: T | Division<T>;
  name?: string;
}

export interface Division<T> {
  dividend: T;
  divisor: T;
}
</script>
