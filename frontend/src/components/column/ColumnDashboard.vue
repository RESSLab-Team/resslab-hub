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
      <v-row v-if="!item">
        <v-col cols="12">
          <column-parallel-chart
            :color="colors.orange"
            :fields="parallelFields"
            :searches.sync="searches"
            :query="query"
          >
            <template v-slot:title>
              <info-tooltip>Parallel Axis</info-tooltip>
            </template>
          </column-parallel-chart>
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item"></v-row>
      <v-row v-else>
        <v-col cols="12">
          <v-card>
            <v-card-title>
              Steel
              <info-tooltip>TODO</info-tooltip>
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" sm="6">
                  <column-single-chart
                    :field="ColumnField.SteelC"
                    :query="query"
                    :searches.sync="searches"
                  ></column-single-chart>
                </v-col>
                <v-col cols="12" sm="6">
                  <column-double-chart
                    :fields="[ColumnField.Date, ColumnField.SteelC]"
                    :query="query"
                    :searches.sync="searches"
                    type="line"
                  ></column-double-chart>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col sm="6">
          <v-card>
            <v-card-title>
              Column Depth [mm]
              <info-tooltip>Column Depth [mm]</info-tooltip>
            </v-card-title>
            <v-card-text>
              <column-double-chart
                :color="colors.red"
                :fields="[ColumnField.DC, ColumnField.Date]"
                :query="query"
                :searches.sync="searches"
              ></column-double-chart>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { ColumnField, ColumnModel } from "@/backend";
import ColumnDoubleChart from "@/components/column/charts/ColumnDoubleChart.vue";
import ColumnParallelChart from "@/components/column/charts/ColumnParallelChart.vue";
import ColumnSingleChart from "@/components/column/charts/ColumnSingleChart.vue";
import ColumnTable from "@/components/column/ColumnTable.vue";
import { ParallelField } from "@/components/commons/charts/SimpleParallelChart.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import { filterColumnValue, globalSearchKey, Searches } from "@/utils/common";
import { Component, Vue } from "vue-property-decorator";
import colors from "vuetify/lib/util/colors";

@Component({
  components: {
    ColumnDoubleChart,
    ColumnParallelChart,
    ColumnSingleChart,
    ColumnTable,
    InfoTooltip,
  },
})
export default class ColumnDashboard extends Vue {
  readonly ColumnField = ColumnField;
  readonly colors = colors;
  readonly fields: string[] = Object.values(ColumnField);
  readonly parallelFields: ParallelField<ColumnField>[] = [
    ColumnField.Date,
    ColumnField.SectionC,
    ColumnField.DC,
  ];

  search = "";
  searches: Searches = {};
  item: ColumnModel | null = null;

  // TODO: refactor
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
    // TODO: refactor
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
