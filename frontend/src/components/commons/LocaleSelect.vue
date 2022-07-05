<template>
  <v-select v-model="item" :items="items" hide-details>
    <template #selection="data">
      {{ $t(prefix + data.item) }}
    </template>
    <template #item="data">
      {{ $t(prefix + data.item) }}
    </template>
  </v-select>
</template>

<script lang="ts">
import { SelectItem } from "@/utils/vuetify";
import { Component, Prop, VModel, Vue } from "vue-property-decorator";

@Component
export default class LocaleSelect extends Vue {
  @VModel({ type: String, default: "" })
  item!: string;
  @Prop({ type: Array as () => SelectItem[], default: [] })
  readonly items!: SelectItem[];
  @Prop({ type: String, default: "" })
  readonly prefix!: string;
}
</script>
