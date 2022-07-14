<template>
  <tr>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <td v-html="text"></td>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <td v-html="unitLabel"></td>
    <td v-for="(value, index) in values" :key="index" class="text-right">
      {{ value }}
    </td>
  </tr>
</template>

<script lang="ts">
import UnitMixin from "@/components/commons/UnitMixin.vue";
import { Component, Prop } from "vue-property-decorator";

@Component
export default class UnitTableRow extends UnitMixin {
  @Prop({ type: String })
  readonly field!: string;
  @Prop({ type: String })
  readonly text!: string;
  @Prop({ type: Array as () => Record<string, number>[] })
  readonly columns!: Record<string, number>[];
  @Prop({ type: Number, default: 2 })
  readonly fractionDigit!: number;

  get formatter(): Intl.NumberFormat {
    return Intl.NumberFormat(undefined, {
      minimumFractionDigits: this.fractionDigit,
      maximumFractionDigits: this.fractionDigit,
    });
  }

  get values(): string[] {
    return this.columns
      .map((d) => d[this.field])
      .map((v) => v / this.ratio)
      .map((v) => this.formatter.format(v));
  }
}

export interface UnitTableRowData {
  key: string;
  text: string;
  unit: string;
  fractionDigit?: number;
}
</script>

<style lang="scss" scoped>
td {
  white-space: nowrap;
}
</style>
