<template>
  <v-responsive :aspect-ratio="aspectRatio">
    <v-chart
      autoresize
      :init-options="initOptions"
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
  TooltipComponentFormatterCallbackParams,
} from "echarts";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { use } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { XAXisOption, YAXisOption } from "echarts/types/dist/shared";
import { merge, round } from "lodash";
import VChart from "vue-echarts";
import { Component, Prop, Vue } from "vue-property-decorator";
import { initOptions, updateOptions } from "@/components/commons/charts/utils";

use([SVGRenderer, LineChart, GridComponent, LegendComponent, TooltipComponent]);

@Component({
  components: {
    VChart,
    UnitMixin,
  },
})
export default class UnitChart extends Vue {
  readonly initOptions = initOptions;
  readonly updateOptions = updateOptions;
  readonly axisLabelMaxDigits = 2;

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
  @Prop({ type: Boolean, default: false })
  readonly legendSide!: boolean;

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
        right: this.legendSide ? 120 : 20,
        bottom: 20,
        containLabel: true,
      },
      legend: {
        type: "scroll",
        top: 0,
        right: this.legendSide ? 0 : undefined,
        orient: this.legendSide ? "vertical" : "horizontal",
      },
      xAxis: {
        name: this.xUnit
          ? `${xAXisOption.name} [${this.xUnitParent.unitLabel}]`
          : xAXisOption.name,
        nameLocation: "middle",
        nameGap: 26,
        max: "dataMax",
        axisLabel: {
          formatter: (value: number) =>
            `${round(value, this.axisLabelMaxDigits)}`,
          hideOverlap: true,
        },
      },
      yAxis: {
        name: this.yUnit
          ? `${yAXisOption.name} [${this.yUnitParent.unitLabel}]`
          : yAXisOption.name,
        nameLocation: "middle",
        nameGap: 50,
        max: "dataMax",
        axisLabel: {
          formatter: (value: number) =>
            `${round(value, this.axisLabelMaxDigits)}`,
          hideOverlap: true,
        },
      },
      tooltip: {
        trigger: "axis",
        confine: true,
        valueFormatter: (value) => (value as number).toFixed(2),
        formatter: (params: TooltipComponentFormatterCallbackParams) => {
          if (!Array.isArray(params)) {
            return "";
          }
          const value = (params[0].value as number[])[0].toFixed(2);
          const suffix = this.yUnit ? ` [${this.yUnitParent.unitLabel}]` : "";
          return [
            `<b>${xAXisOption.name?.split(", ")[0]}: ${value} [${
              this.xUnitParent.unitLabel
            }]</b>`,
            ...params
              .map((param) => {
                if (Array.isArray(param.value)) {
                  const value = param.value[1] as number;
                  const displayValue = value.toFixed(2);
                  return value !== 0
                    ? `${param.marker} ${param.seriesName}: ${displayValue}` +
                        suffix
                    : "";
                }
                return `${param.value}`;
              })
              .filter((text) => text.length > 0),
          ].join("<br />");
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
