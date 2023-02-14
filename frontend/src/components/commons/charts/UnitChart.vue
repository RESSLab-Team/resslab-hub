<script setup lang="ts">
import { initOptions, updateOptions } from "@/components/commons/charts/utils";
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
import { cloneDeep, merge, round } from "lodash";
import VChart from "vue-echarts";
import { withDefaults, defineProps, computed } from "vue";

export interface Props {
  option: EChartsOption;
  unitSystem?: UnitSystem;
  xUnit?: string;
  yUnit?: string;
  aspectRatio?: number;
  maxWidth?: number;
  legendSide?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  unitSystem: undefined,
  xUnit: undefined,
  yUnit: undefined,
  aspectRatio: 1,
  maxWidth: undefined,
  legendSide: false,
});

use([SVGRenderer, LineChart, GridComponent, LegendComponent, TooltipComponent]);

const axisLabelMaxDigits = 2;

const xUnitParent = computed<UnitMixin>(
  () =>
    new UnitMixin({
      propsData: {
        unit: props.xUnit,
        unitSystem: props.unitSystem,
      },
    })
);
const yUnitParent = computed<UnitMixin>(
  () =>
    new UnitMixin({
      propsData: {
        unit: props.yUnit,
        unitSystem: props.unitSystem,
      },
    })
);
const xRatio = computed(() => xUnitParent.value.ratio);
const yRatio = computed(() => yUnitParent.value.ratio);
const actualOption = computed<EChartsOption>(() => {
  const option = cloneDeep(props.option);
  const xAXisOption: XAXisOption = option.xAxis as XAXisOption;
  const yAXisOption: YAXisOption = option.yAxis as YAXisOption;
  const defaultOption: EChartsOption = {
    grid: {
      left: 40,
      top: 40,
      right: props.legendSide ? 180 : 20,
      bottom: 20,
      containLabel: true,
    },
    legend: {
      type: "scroll",
      top: 0,
      right: props.legendSide ? 0 : undefined,
      orient: props.legendSide ? "vertical" : "horizontal",
    },
    xAxis: {
      nameLocation: "middle",
      nameTextStyle: {
        fontWeight: "bold",
      },
      nameGap: 26,
      max: xAXisOption?.max ?? "dataMax",
      axisLabel: {
        formatter: (value: number) => `${round(value, axisLabelMaxDigits)}`,
        hideOverlap: true,
      },
    },
    yAxis: {
      nameLocation: "middle",
      nameTextStyle: {
        fontWeight: "bold",
      },
      nameGap: 70,
      max: yAXisOption?.max ?? "dataMax",
      axisLabel: {
        formatter: (value: number) => `${round(value, axisLabelMaxDigits)}`,
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
        const suffix = props.yUnit ? ` [${yUnitParent.value.unitLabel}]` : "";
        return [
          `<b>${xAXisOption?.name?.split(", ")[0]}: ${value} [${
            xUnitParent.value.unitLabel
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
  };
  const overrideOption: EChartsOption = {
    xAxis: {
      name: props.xUnit
        ? `${xAXisOption.name} [${xUnitParent.value.unitLabel}]`
        : xAXisOption.name,
    },
    yAxis: {
      name: props.yUnit
        ? `${yAXisOption.name} [${yUnitParent.value.unitLabel}]`
        : yAXisOption.name,
    },
    series: (option.series as SeriesOption[]).map((serie) =>
      merge(serie, {
        data: (serie.data as [number, number][]).map((v) => [
          v[0] * xRatio.value,
          v[1] * yRatio.value,
        ]),
      })
    ),
  };
  return merge(defaultOption, option, overrideOption);
});
</script>

<template>
  <v-responsive :aspect-ratio="aspectRatio" :max-width="maxWidth">
    <v-chart
      autoresize
      :init-options="initOptions"
      :option="actualOption"
      :update-options="updateOptions"
    />
  </v-responsive>
</template>
