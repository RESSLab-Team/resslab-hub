<template>
  <v-responsive aspect-ratio="1">
    <v-chart
      autoresize
      :option="actualOption"
      :update-options="updateOptions"
    ></v-chart>
  </v-responsive>
</template>

<script lang="ts">
import UnitParent from "@/components/commons/UnitParent.vue";
import { UnitSystem } from "@/utils/unit";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
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

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent]);

@Component({
  components: {
    VChart,
    UnitParent,
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

  get xUnitParent(): UnitParent {
    return new UnitParent({
      propsData: {
        unit: this.xUnit,
        unitSystem: this.unitSystem,
      },
    });
  }

  get yUnitParent(): UnitParent {
    return new UnitParent({
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
      xAxis: {
        name: `${xAXisOption.name} [${this.xUnitParent.unitLabel}]`,
      },
      yAxis: {
        name: `${yAXisOption.name} [${this.yUnitParent.unitLabel}]`,
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
