<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <column-table
            :search.sync="search"
            :searches.sync="searches"
            :query="query"
            @click="click"
          ></column-table>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { ColumnField, ColumnModel } from "@/backend";
import ColumnTable from "@/components/column/ColumnTable.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import { filterColumnValue, globalSearchKey, Searches } from "@/utils/common";
import { Component, Vue } from "vue-property-decorator";
import colors from "vuetify/lib/util/colors";
import { ParallelField } from "../commons/charts/SimpleParallelChart.vue";

@Component({
  components: {
    ColumnTable,
    InfoTooltip,
  },
})
export default class ColumnDashboard extends Vue {
  readonly ColumnField = ColumnField;
  readonly colors = colors;
  readonly fields: string[] = Object.values(ColumnField);
  readonly parallelFields: ParallelField<ColumnField>[] = [ColumnField.Date];

  search = "";
  searches: Searches = {};
  item: ColumnModel | null = null;

  get query(): string {
    const queries = Object.entries(this.searches)
      .filter(([, value]) => filterColumnValue(value))
      .map(([key, value]) => `${key}:${value}`);
    if (this.search && this.search.length > 0) {
      queries.push(`%${this.search}%`);
    }
    return queries.join(";");
  }

  created(): void {
    Object.entries(this.$route.query)
      .filter(([key, value]) => this.fields.includes(key) && value.length > 0)
      .forEach(([key, value]) => {
        this.$set(this.searches, key, value);
      });
    const globalSearchValue = this.$route.query[globalSearchKey];
    if (typeof globalSearchValue === "string") {
      this.search = globalSearchValue;
    }
  }

  click(item: ColumnModel): void {
    this.item = item;
  }

  close(): void {
    this.item = null;
  }
}
</script>
