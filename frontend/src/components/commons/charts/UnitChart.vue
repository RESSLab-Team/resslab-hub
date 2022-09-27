<template>
  <v-responsive :aspect-ratio="aspectRatio">
    <v-chart
      autoresize
      :option="actualOption"
      :update-options="updateOptions"
    ></v-chart>
  </v-responsive>
</template>

<script lang="ts">
import UnitMixin from "@/components/commons/UnitMixin.vue";
import { UnitSystem } from "@/utils/unit";
import {
  EChartsOption,
  SeriesOption,
  SetOptionOpts,
  TooltipComponentFormatterCallbackParams,
} from "echarts";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { XAXisOption, YAXisOption } from "echarts/types/dist/shared";
import { merge } from "lodash";
import VChart from "vue-echarts";
import { Component, Prop, Vue } from "vue-property-decorator";

use([
  CanvasRenderer,
  LineChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
]);

@Component({
  components: {
    VChart,
    UnitMixin,
  },
})
export default class UnitChart extends Vue {
  readonly updateOptions: SetOptionOpts = {
    notMerge: true,
  };

  @Prop({ type: Object as () => EChartsOption })
  readonly option!: EChartsOption;
  @Prop({ type: String as () => UnitSystem })
  readonly unitSystem: UnitSystem | undefined;
  @Prop({ type: String })
  readonly xUnit: string | undefined;
  @Prop({ type: String })
  readonly yUnit: string | undefined;
  @Prop({ type: Number, default: 1 })
  readonly aspectRatio!: number;

  get xUnitParent(): UnitMixin {
    return new UnitMixin({
      propsData: {
        unit: this.xUnit,
        unitSystem: this.unitSystem,
      },
    });
  }

  get yUnitParent(): UnitMixin {
    return new UnitMixin({
      propsData: {
        unit: this.yUnit,
        unitSystem: this.unitSystem,
      },
    });
  }

  get xRatio(): number {
    return this.xUnitParent.ratio;
  }

  get yRatio(): number {
    return this.yUnitParent.ratio;
  }

  get actualOption(): EChartsOption {
    const xAXisOption: XAXisOption = this.option.xAxis as XAXisOption;
    const yAXisOption: YAXisOption = this.option.yAxis as YAXisOption;
    const changedOption: EChartsOption = {
      grid: {
        left: 40,
        top: 40,
        right: 20,
        bottom: 20,
        containLabel: true,
      },
      legend: {
        type: "scroll",
        top: 0,
      },
      xAxis: {
        name: `${xAXisOption.name} [${this.xUnitParent.unitLabel}]`,
        nameLocation: "middle",
        nameGap: 26,
      },
      yAxis: {
        name: `${yAXisOption.name} [${this.yUnitParent.unitLabel}]`,
        nameLocation: "middle",
        nameGap: 70,
      },
      tooltip: {
        trigger: "axis",
        confine: true,
        valueFormatter: (value) => (value as number).toFixed(2),
        formatter: (params: TooltipComponentFormatterCallbackParams) => {
          if (Array.isArray(params)) {
            const value = (params[0].value as number[])[0].toFixed(2);
            return [
              `<b>${xAXisOption.name?.split(", ")[0]}: ${value} [${
                this.xUnitParent.unitLabel
              }]</b>`,
              ...params
                .map((param) => {
                  if (Array.isArray(param.value)) {
                    const value = param.value[1] as number;
                    return value !== 0
                      ? `${param.marker} ${param.seriesName}: ${value.toFixed(
                          2
                        )} [${this.yUnitParent.unitLabel}]`
                      : "";
                  }
                  return `${param.value}`;
                })
                .filter((text) => text.length > 0),
            ].join("<br />");
          } else {
            return "";
          }
        },
      },
      series: (this.option.series as SeriesOption[]).map((serie) =>
        merge({}, serie, {
          data: (serie.data as [number, number][]).map((v) => [
            v[0] * this.xRatio,
            v[1] * this.yRatio,
          ]),
        })
      ),
    };
    return merge({}, this.option, changedOption);
  }
}
</script>
