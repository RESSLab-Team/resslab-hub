<template>
  <v-select
    v-model="model"
    clearable
    hide-details
    :items="actualItems"
    :label="label"
    single-line
  >
    <template #prepend-item>
      <v-list-item>
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          clearable
          :hint="hint"
          persistent-hint
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
  @VModel({ type: Object as () => SelectItem })
  model!: string;
  @Prop({ type: Array as () => SelectItem[], default: () => [] })
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

  get hint(): string {
    return `${this.actualItems.length} items`;
  }

  @Watch("items")
  onItemsChanged(): void {
    this.search = null;
  }
}
</script>
