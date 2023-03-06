<script setup lang="ts">
import { useUnits } from "@/utils/unit";
import { withDefaults, defineProps, computed } from "vue";

export interface UnitTableRowData {
  key: string;
  text: string;
  unit: string;
  fractionDigit?: number;
}

const props = withDefaults(
  defineProps<{
    unit?: string;
    field: string;
    text: string;
    columns?: Record<string, number | undefined>[];
    fractionDigit?: number;
  }>(),
  {
    unit: undefined,
    columns: () => [],
    fractionDigit: 2,
  }
);

const { ratio, unitLabel } = useUnits(props.unit);

const formatter = computed(() =>
  Intl.NumberFormat(undefined, {
    minimumFractionDigits: props.fractionDigit,
    maximumFractionDigits: props.fractionDigit,
  })
);
const values = computed(() =>
  props.columns
    .map((d) => d[props.field])
    .map((v) =>
      v !== undefined ? formatter.value.format(v / ratio.value) : ""
    )
);
</script>

<template>
  <tr>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <td v-html="text" />
    <!-- eslint-disable-next-line vue/no-v-html -->
    <td v-html="unitLabel" />
    <td v-for="(value, index) in values" :key="index" class="text-right">
      {{ value }}
    </td>
  </tr>
</template>

<style lang="scss" scoped>
td {
  white-space: nowrap;
}
</style>
