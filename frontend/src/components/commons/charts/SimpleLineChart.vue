<template>
  <multiple-line-chart
    :colors="[color]"
    :max-width="maxWidth"
    :promises="[promise]"
    :title="title"
    :x-axis-name="xAxisName"
    :y-axis-name="yAxisName"
  ></multiple-line-chart>
</template>

<script lang="ts">
import MultipleLineChart, {
  Response,
} from "@/components/commons/charts/MultipleLineChart.vue";
import { primaryColor } from "@/utils/vuetify";
import { Component, Prop, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component({
  components: {
    MultipleLineChart,
  },
})
export default class SimpleLineChart extends Vue {
  @Prop({ type: Object as () => Color, default: () => primaryColor })
  readonly color!: Color;
  @Prop({ type: Number, default: 300 })
  readonly maxWidth!: number;
  @Prop({ type: Promise })
  readonly promise: Promise<Response> | undefined;
  @Prop({ type: String })
  readonly title: string | undefined;
  @Prop({ type: String })
  readonly xAxisName: string | undefined;
  @Prop({ type: String })
  readonly yAxisName: string | undefined;
}
</script>
