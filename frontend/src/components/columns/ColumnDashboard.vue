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
          </column-parallel-chart>
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12">
          <column-detail :value="item" @close="close"></column-detail>
        </v-col>
      </v-row>
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
            <column-depth-card-title></column-depth-card-title>
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
            <steel-type-card-title></steel-type-card-title>
            <v-card-text>
              <column-single-chart
                :color="colors.green"
                :field="steelField"
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
import ColumnDetail from "@/components/columns/ColumnDetail.vue";
import ColumnTable from "@/components/columns/ColumnTable.vue";
import { DoubleFields } from "@/components/commons/charts/DoubleChart.vue";
import { ParallelField } from "@/components/commons/charts/SimpleParallelChart.vue";
import ColumnDepthCardTitle from "@/components/commons/ColumnDepthCardTitle.vue";
import DashboardMixin from "@/components/commons/DashboardMixin.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SteelTypeCardTitle from "@/components/commons/SteelTypeCardTitle.vue";
import { Component } from "vue-property-decorator";
import colors from "vuetify/lib/util/colors";

@Component({
  components: {
    ColumnDepthCardTitle,
    ColumnDetail,
    ColumnDoubleChart,
    ColumnParallelChart,
    ColumnSingleChart,
    ColumnTable,
    InfoTooltip,
    SteelTypeCardTitle,
  },
})
export default class ColumnDashboard extends DashboardMixin<ColumnModel> {
  readonly colors = colors;
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
  readonly steelField = ColumnField.SteelC;

  get fields(): string[] {
    return Object.values(ColumnField);
  }
}
</script>
