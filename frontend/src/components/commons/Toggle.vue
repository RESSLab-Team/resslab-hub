<template>
  <v-btn-toggle v-model="index" mandatory>
    <v-btn v-for="item in items" :key="item">{{ item }}</v-btn>
  </v-btn-toggle>
</template>

<script lang="ts">
import { Component, Prop, VModel, Vue } from "vue-property-decorator";

@Component
export default class Toggle extends Vue {
  @VModel({ type: String })
  item!: string;
  @Prop({ type: Array as () => string[] })
  readonly items!: string[];

  get index(): number {
    return this.items.indexOf(this.item) ?? 0;
  }

  set index(value: number) {
    this.item = this.items[value];
  }
}
</script>
