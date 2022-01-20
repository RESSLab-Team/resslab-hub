<template>
  <v-select
    v-model="model"
    clearable
    hide-details
    :items="actualItems"
    :label="label"
    single-line
  >
    <template v-slot:prepend-item>
      <v-list-item>
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          clearable
          hide-details
          single-line
          solo
        ></v-text-field>
      </v-list-item>
    </template>
  </v-select>
</template>

<script lang="ts">
import { SelectItem } from "@/utils/vuetify";
import { Component, Prop, VModel, Vue, Watch } from "vue-property-decorator";

@Component
export default class SearchSelect extends Vue {
  @VModel({ type: String })
  model!: string;
  @Prop({ type: Array as () => string[], default: () => [] })
  readonly items!: SelectItem[];
  @Prop({ type: String })
  readonly label: string | undefined;

  private search: string | null = null;

  get actualItems(): SelectItem[] {
    if (!this.search) {
      return this.items;
    }
    const substring = this.search.toLowerCase();
    return this.items.filter((item) => {
      const value = typeof item === "string" ? item : item.text.toString();
      return value.toLowerCase().includes(substring);
    });
  }

  @Watch("items")
  onItemsChanged(): void {
    this.search = null;
  }
}
</script>
