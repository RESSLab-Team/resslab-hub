<template>
  <tr>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <td v-html="text"></td>
    <!-- eslint-disable-next-line vue/no-v-html -->
    <td v-html="unitLabel"></td>
    <td v-for="(value, index) in values" :key="index">
      {{ value }}
    </td>
  </tr>
</template>

<style lang="scss" scoped>
td {
  white-space: nowrap;
}
</style>

<script lang="ts">
import UnitParent from "@/components/commons/UnitParent.vue";
import { Component, Prop } from "vue-property-decorator";

@Component
export default class UnitTableRow extends UnitParent {
  @Prop({ type: String })
  readonly field!: string;
  @Prop({ type: String })
  readonly text!: string;
  @Prop({ type: Array as () => Record<string, number>[] })
  readonly columns!: Record<string, number>[];

  get values(): string[] {
    return this.columns
      .map((d) => d[this.field])
      .map((v) => v * this.ratio)
      .map((v) => v.toLocaleString());
  }
}

export interface UnitTableRowData {
  key: string;
  text: string;
  unit: string;
}
</script>
