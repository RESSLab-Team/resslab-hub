<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <brace-table
            :search.sync="search"
            :searches.sync="searches"
            :query="query"
            @click="click"
            @loadPage="loadPage"
          ></brace-table>
        </v-col>
      </v-row>
      <v-row v-if="!item">
        <v-col cols="12">
          <brace-parallel-chart
            :color="colors.orange"
            :fields="parallelFields"
            :searches.sync="searches"
            :query="query"
          >
            <template #title>
              <info-tooltip>Parallel Axis</info-tooltip>
            </template>
          </brace-parallel-chart>
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12">
          <brace-detail :value="item" @close="close"></brace-detail>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Boundary Condition</v-card-title>
            <v-card-text>
              <brace-double-chart
                :fields="boundaryConditionFields"
                :query="query"
                :searches.sync="searches"
                type="line"
              ></brace-double-chart>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>Loading Protocol</v-card-title>
            <v-card-text>
              <brace-single-chart
                :color="colors.blue"
                :field="loadingProtocolField"
                :query="query"
                :searches.sync="searches"
                type="line"
              ></brace-single-chart>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card>
            <v-card-title>Steel Material</v-card-title>
            <v-card-text>
              <brace-single-chart
                :color="colors.green"
                :field="steelField"
                :query="query"
                :searches.sync="searches"
              ></brace-single-chart>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { BraceField, BraceModel } from "@/backend";
import BraceDetail from "@/components/braces/BraceDetail.vue";
import BraceTable from "@/components/braces/BraceTable.vue";
import BraceDoubleChart from "@/components/braces/charts/BraceDoubleChart.vue";
import BraceParallelChart from "@/components/braces/charts/BraceParallelChart.vue";
import BraceSingleChart from "@/components/braces/charts/BraceSingleChart.vue";
import { DoubleFields } from "@/components/commons/charts/DoubleChart.vue";
import { ParallelField } from "@/components/commons/charts/SimpleParallelChart.vue";
import DashboardMixin from "@/components/commons/DashboardMixin.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import { Component } from "vue-property-decorator";
import colors from "vuetify/lib/util/colors";

@Component({
  components: {
    BraceDetail,
    BraceDoubleChart,
    BraceParallelChart,
    BraceSingleChart,
    BraceTable,
    InfoTooltip,
  },
})
export default class BraceDashboard extends DashboardMixin<BraceModel> {
  readonly colors = colors;
  readonly parallelFields: ParallelField<BraceField>[] = [
    { id: BraceField.KlR },
    {
      id: {
        dividend: BraceField.DBr,
        divisor: BraceField.TBr,
      },
    },
    { id: BraceField.CrossSectionShape },
    { id: BraceField.BoundaryCondition },
  ];
  readonly boundaryConditionFields: DoubleFields<BraceField> = [
    BraceField.Date,
    BraceField.BoundaryCondition,
  ];
  readonly loadingProtocolField = BraceField.LoadingProtocol;
  readonly steelField = BraceField.Steel;

  get fields(): string[] {
    return Object.values(BraceField);
  }
}
</script>
