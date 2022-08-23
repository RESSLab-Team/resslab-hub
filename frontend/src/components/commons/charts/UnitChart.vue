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
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import {
  EChartsOption,
  SeriesOption,
  SetOptionOpts,
  XAXisOption,
  YAXisOption,
} from "echarts/types/dist/shared";
import _ from "lodash";
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
  @Prop({ type: Number, default: () => 1 })
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
      },
      series: (this.option.series as SeriesOption[]).map((serie) =>
        _.merge({}, serie, {
          data: (serie.data as [number, number][]).map((v) => [
            v[0] * this.xRatio,
            v[1] * this.yRatio,
          ]),
        })
      ),
    };
    return _.merge({}, this.option, changedOption);
  }
}
</script>
