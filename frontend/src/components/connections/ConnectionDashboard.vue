<script setup lang="ts">
import { ConnectionField, ConnectionModel } from "@/backend";
import { DoubleFields } from "@/components/commons/charts/DoubleChart.vue";
import { ParallelField } from "@/components/commons/charts/SimpleParallelChart.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import SteelTypeCardTitle from "@/components/commons/SteelTypeCardTitle.vue";
import ConnectionDoubleChart from "@/components/connections/charts/ConnectionDoubleChart.vue";
import ConnectionParallelChart from "@/components/connections/charts/ConnectionParallelChart.vue";
import ConnectionSingleChart from "@/components/connections/charts/ConnectionSingleChart.vue";
import ConnectionDetail from "@/components/connections/ConnectionDetail.vue";
import ConnectionTable from "@/components/connections/ConnectionTable.vue";
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
} = useDashboard<ConnectionModel>(route, ConnectionField);

const parallelFields: ParallelField<ConnectionField>[] = [
  {
    id: ConnectionField.DB,
    name: "Beam Depth\ndb [mm]",
  },
  {
    id: ConnectionField.DC,
    name: "Column Depth\ndc [mm]",
  },
  {
    id: ConnectionField.TCf,
    name: "Column flange\nThickness [mm]",
  },
  {
    id: {
      dividend: ConnectionField.DB,
      divisor: ConnectionField.DC,
    },
    name: "db / dc",
  },
  {
    id: ConnectionField.GMaxGY,
  },
  {
    id: ConnectionField.RuRnPlN,
  },
  {
    id: ConnectionField.ConnectionType,
    name: "Connection\nType",
  },
];
const beamFields: DoubleFields<ConnectionField> = [
  ConnectionField.DB,
  {
    id: ConnectionField.Slab,
    mapping: new Map([
      ["False", "Bare"],
      ["True", "Composite"],
    ]),
  },
];
</script>

<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <connection-table
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
          <connection-parallel-chart
            :color="colors.orange"
            :fields="parallelFields"
            :searches.sync="searches"
            :query="query"
          />
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12">
          <connection-detail :connection="item" @close="closeDetail" />
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12">
          <v-card>
            <v-card-title>
              Connection Type
              <info-tooltip>
                <p>
                  This rectangle below displays the proportion of each
                  connection type in the database. Connection types are
                  categorised according to AISC-358-16 Prequalified connections.
                  See also the evolution of connection types studied over the
                  years on the right.
                </p>
                How to use?
                <ul>
                  <li>
                    See the connection type drawing by hovering over the
                    corresponding type in the rectangle
                  </li>
                  <li>
                    Filter the Database for a specific connection type or dates
                    by clicking on the rectangle of using the dates sliders
                  </li>
                </ul>
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" sm="6">
                  <connection-single-chart
                    :field="ConnectionField.ConnectionType"
                    :query="query"
                    :searches.sync="searches"
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <connection-double-chart
                    :fields="[
                      ConnectionField.Date,
                      ConnectionField.ConnectionType,
                    ]"
                    :query="query"
                    :searches.sync="searches"
                    type="line"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col sm="6">
          <v-card>
            <v-card-title>
              Beam Depth [mm]
              <info-tooltip>
                <p>
                  This histogram displays the distribution of column depths in
                  the Database.
                </p>
                How to use?
                <ul>
                  <li>
                    Filter database for specific column depths, by clicking on a
                    bar or using the slider below
                  </li>
                  <li>
                    Filter database depending on the presence of doubler plates
                    welded in the panel zone (0/1/2) by clicking on the legend.
                  </li>
                </ul>
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <connection-double-chart
                :color="colors.blue"
                :fields="beamFields"
                :query="query"
                :searches.sync="searches"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col sm="6">
          <v-card>
            <v-card-title>
              Column Depth [mm]
              <info-tooltip>
                <p>
                  This histogram displays the distribution of column depths in
                  the Database.
                </p>
                How to use?
                <ul>
                  <li>
                    Filter database for specific column depths, by clicking on a
                    bar or using the slider below
                  </li>
                  <li>
                    Filter database depending on the presence of doubler plates
                    welded in the panel zone (0/1/2) by clicking on the legend.
                  </li>
                </ul>
              </info-tooltip>
            </v-card-title>
            <v-card-text>
              <connection-double-chart
                :color="colors.green"
                :fields="[ConnectionField.DC, ConnectionField.NDp]"
                :query="query"
                :searches.sync="searches"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card>
            <steel-type-card-title />
            <v-card-text>
              <connection-single-chart
                :color="colors.deepPurple"
                :field="ConnectionField.SteelB"
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
