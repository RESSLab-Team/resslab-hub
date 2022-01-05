<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <connection-table
            :search.sync="search"
            :searches.sync="searches"
            :query="query"
            @click="onClick"
          ></connection-table>
        </v-col>
      </v-row>
      <v-row v-if="!connection">
        <v-col cols="12">
          <connection-parallel-chart
            :color="colors.orange"
            :fields="parallelFields"
            :searches.sync="searches"
            :query="query"
          >
            <template v-slot:title>
              <info-tooltip>Parallel Axis</info-tooltip>
            </template>
          </connection-parallel-chart>
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="connection">
        <v-col cols="12">
          <connection-detail
            :connection="connection"
            @close="onClose"
          ></connection-detail>
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12">
          <v-card>
            <v-card-title>
              Connection Type
              <info-tooltip>Connection Type</info-tooltip>
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" sm="6">
                  <connection-single-chart
                    :field="ConnectionField.ConnectionType"
                    :query="query"
                    :searches.sync="searches"
                  ></connection-single-chart>
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
                  ></connection-double-chart>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col sm="6">
          <v-card>
            <v-card-title>
              Beam Depth [mm]
              <info-tooltip>Beam Depth [mm]</info-tooltip>
            </v-card-title>
            <v-card-text>
              <connection-double-chart
                :color="colors.red"
                :fields="[ConnectionField.DB, ConnectionField.Slab]"
                :query="query"
                :searches.sync="searches"
              ></connection-double-chart>
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
              <connection-double-chart
                :color="colors.green"
                :fields="[ConnectionField.DC, ConnectionField.NDp]"
                :query="query"
                :searches.sync="searches"
              ></connection-double-chart>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12">
          <v-card>
            <v-card-title>
              Steel Material
              <info-tooltip>Steel Material</info-tooltip>
            </v-card-title>
            <v-card-text>
              <connection-single-chart
                :color="colors.deepPurple"
                :field="ConnectionField.SteelB"
                :query="query"
                :searches.sync="searches"
              ></connection-single-chart>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { ConnectionField, ConnectionModel } from "@/backend";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import LocaleSelect from "@/components/commons/LocaleSelect.vue";
import ConnectionDoubleChart from "@/components/connection/charts/ConnectionDoubleChart.vue";
import ConnectionParallelChart, {
  Field,
} from "@/components/connection/charts/ConnectionParallelChart.vue";
import ConnectionSingleChart from "@/components/connection/charts/ConnectionSingleChart.vue";
import ConnectionDetail from "@/components/connection/ConnectionDetail.vue";
import ConnectionTable from "@/components/connection/ConnectionTable.vue";
import { filterColumnValue, globalSearchKey, Searches } from "@/utils/common";
import { Component, Vue } from "vue-property-decorator";
import colors from "vuetify/lib/util/colors";

@Component({
  components: {
    ConnectionTable,
    LocaleSelect,
    ConnectionSingleChart,
    ConnectionDoubleChart,
    ConnectionParallelChart,
    ConnectionDetail,
    InfoTooltip,
  },
})
export default class ConnectionDashboard extends Vue {
  readonly ConnectionField = ConnectionField;
  readonly colors = colors;
  readonly fields: string[] = Object.values(ConnectionField);
  readonly parallelFields: Field[] = [
    ConnectionField.DB,
    ConnectionField.DC,
    ConnectionField.TCf,
    {
      dividend: ConnectionField.DB,
      divisor: ConnectionField.DC,
    },
    ConnectionField.GMaxGY,
    ConnectionField.RuRnPlN,
    ConnectionField.ConnectionType,
  ];

  search = "";
  searches: Searches = {};
  connection: ConnectionModel | null = null;

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

  onClick(connection: ConnectionModel): void {
    this.connection = connection;
  }

  onClose(): void {
    this.connection = null;
  }
}
</script>
