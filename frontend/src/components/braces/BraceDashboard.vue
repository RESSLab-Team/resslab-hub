<script setup lang="ts">
import { BraceField, BraceModel } from "@/backend";
import BraceDetail from "@/components/braces/BraceDetail.vue";
import BraceTable from "@/components/braces/BraceTable.vue";
import BraceDoubleChart from "@/components/braces/charts/BraceDoubleChart.vue";
import BraceParallelChart from "@/components/braces/charts/BraceParallelChart.vue";
import BraceSingleChart from "@/components/braces/charts/BraceSingleChart.vue";
import { DoubleFields } from "@/components/commons/charts/DoubleChart.vue";
import { ParallelField } from "@/components/commons/charts/SimpleParallelChart.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SteelTypeCardTitle from "@/components/commons/SteelTypeCardTitle.vue";
import { useRoute } from "vue-router/composables";
import colors from "vuetify/lib/util/colors";
import { useDashboard } from "@/utils/dashboard";

const route = useRoute();
const {
  clickTableRow,
  closeDetail,
  item,
  query,
  search,
  searches,
  updatePage,
} = useDashboard<BraceModel>(route, BraceField);

const parallelFields: ParallelField<BraceField>[] = [
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
const boundaryConditionFields: DoubleFields<BraceField> = [
  BraceField.Date,
  BraceField.BoundaryCondition,
];
const loadingProtocolField = BraceField.LoadingProtocol;
const steelField = BraceField.Steel;
</script>

<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <brace-table
            :search.sync="search"
            :searches.sync="searches"
            :query="query"
            @click:row="clickTableRow"
            @update:page="updatePage"
          />
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
          <brace-detail :brace="item" @close="closeDetail" />
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
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title>
              Loading Protocol
              <info-tooltip>
                <p>
                  This rectangle below displays the proportion of each loading
                  protocol in the database. See also the evolution of test data
                  over the years on the right.
                </p>
                How to use?
                <ul>
                  <li>
                    Filter the Database for a specific loading protocol type or
                    dates by clicking on the rectangle of using the dates
                    sliders.
                  </li>
                </ul>
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <brace-single-chart
                :color="colors.blue"
                :field="loadingProtocolField"
                :query="query"
                :searches.sync="searches"
                type="line"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card>
            <steel-type-card-title />
            <v-card-text>
              <brace-single-chart
                :color="colors.deepPurple"
                :field="steelField"
                :query="query"
                :searches.sync="searches"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
