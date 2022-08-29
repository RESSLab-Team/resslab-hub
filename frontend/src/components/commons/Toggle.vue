<template>
  <v-btn-toggle v-model="index" mandatory>
    <v-btn v-for="item in items" :key="item.value">{{ item.text }}</v-btn>
  </v-btn-toggle>
</template>

<script lang="ts">
import { UnitSystem } from "@/utils/unit";
import { Component, Prop, VModel, Vue } from "vue-property-decorator";

@Component
export default class Toggle<V extends string = string> extends Vue {
  @VModel({ type: String })
  item!: V;
  @Prop({ type: Array as () => ToggleItem<V>[] })
  readonly items!: ToggleItem<V>[];

  get index(): number {
    return this.items.findIndex((item) => item.value === this.item) ?? 0;
  }

  set index(value: number) {
    this.item = this.items[value].value;
  }
}

export interface ToggleItem<V extends string = string> {
  value: V;
  text: string;
}

export const unitItems: ToggleItem<UnitSystem>[] = [
  {
    value: "metric",
    text: "Metric",
  },
  {
    value: "imperial",
    text: "Imperial",
  },
];
</script>
