<script setup lang="ts">
import { initOptions, updateOptions } from "@/components/commons/charts/utils";
import { Count } from "@/composables/chart";
import { getColorPalette, primaryColor } from "@/utils/vuetify";
import { EChartsOption } from "echarts";
import { TreemapChart } from "echarts/charts";
import { TooltipComponent } from "echarts/components";
import { use } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { CallbackDataParams } from "echarts/types/dist/shared";
import VChart from "vue-echarts";
import { withDefaults, defineProps, computed, defineEmits } from "vue";
import { Color } from "vuetify/lib/util/colors";
import { Value } from "@/utils/common";
import i18n from "@/i18n";

use([SVGRenderer, TreemapChart, TooltipComponent]);

const props = withDefaults(
  defineProps<{
    color?: Color;
    counts?: Count[];
    field: string;
    labelPrefix?: string;
  }>(),
  {
    color: () => primaryColor,
    counts: () => [],
    labelPrefix: "",
  }
);
const emit = defineEmits<{
  (e: "change:searches", key: string, value: Value): void;
  (e: "mouseover", value: CallbackDataParams): void;
  (e: "mouseout"): void;
}>();

const option = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: "item",
    confine: true,
  },
  series: [
    {
      type: "treemap",
      id: props.field,
      name: i18n.t(props.labelPrefix + props.field).toString(),
      left: 0,
      top: 0,
      right: 0,
      bottom: 0,
      data: props.counts.map((count) => {
        return {
          name: count.name,
          value: count.value,
        };
      }),
      breadcrumb: {
        show: false,
      },
      roam: false,
    },
  ],
  color: getColorPalette(props.color, props.counts.length),
}));

function click(params: CallbackDataParams): void {
  if (params.seriesId) {
    emit("change:searches", params.seriesId, params.name);
  }
}
</script>

<template>
  <div>
    <v-responsive min-height="100">
      <v-chart
        autoresize
        :init-options="initOptions"
        :option="option"
        :update-options="updateOptions"
        @click="click"
        @mouseover="emit('mouseover', $event)"
        @mouseout="emit('mouseout')"
      />
    </v-responsive>
    <slot />
  </div>
</template>
