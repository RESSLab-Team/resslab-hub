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
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Boundary Condition</v-card-title>
            <v-card-text>
              <column-double-chart
                :fields="boundaryConditionFields"
                :query="query"
                :searches.sync="searches"
                type="line"
              ></column-double-chart>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>
              Column Depth [mm]
              <info-tooltip>Column Depth [mm]</info-tooltip>
            </v-card-title>
            <v-card-text>
              <column-double-chart
                :color="colors.red"
                :fields="columnDepthFields"
                :query="query"
                :searches.sync="searches"
              ></column-double-chart>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card>
            <v-card-title>Steel Material</v-card-title>
            <v-card-text>
              <column-single-chart
                :color="colors.green"
                :field="ColumnField.SteelC"
                :query="query"
                :searches.sync="searches"
              ></column-single-chart>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { ColumnField, ColumnModel } from "@/backend";
import ColumnDoubleChart from "@/components/columns/charts/ColumnDoubleChart.vue";
import ColumnParallelChart from "@/components/columns/charts/ColumnParallelChart.vue";
import ColumnSingleChart from "@/components/columns/charts/ColumnSingleChart.vue";
import ColumnTable from "@/components/columns/ColumnTable.vue";
import { ParallelField } from "@/components/commons/charts/SimpleParallelChart.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import { filterColumnValue, globalSearchKey, Searches } from "@/utils/common";
import { Component, Vue } from "vue-property-decorator";
import colors from "vuetify/lib/util/colors";
import { DoubleFields } from "../commons/charts/DoubleChart.vue";

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
    { id: ColumnField.Th80 },
    { id: ColumnField.HOverTCw },
    { id: ColumnField.BFOverTCf },
    { id: ColumnField.LBOverRYc },
    { id: ColumnField.PGOverPYm },
  ];
  readonly boundaryConditionFields: DoubleFields<ColumnField> = [
    ColumnField.Date,
    ColumnField.BoundaryCondition,
  ];
  readonly columnDepthFields: DoubleFields<ColumnField> = [
    ColumnField.DC,
    {
      id: ColumnField.BuiltUp,
      mapping: new Map([
        ["False", "Hot Rolled"],
        ["True", "Built Up"],
      ]),
    },
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
