<script setup lang="ts">
import { MaterialField, MaterialModel } from "@/backend";
import { DoubleFields } from "@/components/commons/charts/DoubleChart.vue";
import { ParallelField } from "@/components/commons/charts/SimpleParallelChart.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import MaterialDoubleChart from "@/components/materials/charts/MaterialDoubleChart.vue";
import MaterialParallelChart from "@/components/materials/charts/MaterialParallelChart.vue";
import MaterialSingleChart from "@/components/materials/charts/MaterialSingleChart.vue";
import MaterialDetail from "@/components/materials/MaterialDetail.vue";
import MaterialTable from "@/components/materials/MaterialTable.vue";
import { useDashboard } from "@/utils/dashboard";
import { useRoute } from "vue-router/composables";
import colors from "vuetify/lib/util/colors";

const route = useRoute();
const {
  clickTableRow,
  closeDetail,
  item,
  query,
  search,
  searches,
  updatePage,
} = useDashboard<MaterialModel>(route, MaterialField);

const parallelFields: ParallelField<MaterialField>[] = [
  { id: MaterialField.Type },
  { id: MaterialField.YieldStressMpa },
  {
    id: {
      dividend: MaterialField.YieldStressMpa,
      divisor: MaterialField.FyNMpa,
    },
  },
  { id: MaterialField.FractureStrain },
  { id: MaterialField.Thickness },
];
const profileFields: DoubleFields<MaterialField> = [
  MaterialField.Date,
  MaterialField.Profile,
];
const profileThicknessFields: DoubleFields<MaterialField> = [
  MaterialField.Thickness,
  MaterialField.Profile,
];
const steelField = MaterialField.Type;
</script>

<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <material-table
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
          <material-parallel-chart
            :color="colors.orange"
            :fields="parallelFields"
            :searches.sync="searches"
            :query="query"
          >
            <template #title>
              <info-tooltip>Parallel Axis</info-tooltip>
            </template>
          </material-parallel-chart>
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12">
          <material-detail :material="item" @close="closeDetail" />
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12">
          <v-card>
            <v-card-title>Profile Type</v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <material-double-chart
                    :fields="profileFields"
                    :query="query"
                    :searches.sync="searches"
                    type="line"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <material-double-chart
                    :fields="profileThicknessFields"
                    :query="query"
                    :searches.sync="searches"
                    type="bar"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card>
            <v-card-title>Steel Material Type</v-card-title>
            <v-card-text>
              <material-single-chart
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
