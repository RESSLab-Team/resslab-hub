<template>
  <div>
    <v-row>
      <v-col cols="6">
        <v-row>
          <v-col>
            <connection-table
              :search.sync="search"
              :searches.sync="searches"
              :query="query"
            ></connection-table>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-card>
              <v-card-title>Parallel Axis</v-card-title>
              <v-card-text>
                <connection-parallel-chart
                  :fields="parallelFields"
                  :searches.sync="searches"
                  :query="query"
                ></connection-parallel-chart>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-col>
      <v-col cols="6">
        <v-row>
          <v-col cols="12">
            <v-card>
              <v-card-title>Connection Type</v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="6">
                    <connection-single-chart
                      :field="ConnectionField.ConnectionType"
                      :query="query"
                      :searches.sync="searches"
                    ></connection-single-chart>
                  </v-col>
                  <v-col cols="6">
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
          <v-col cols="6">
            <v-card>
              <v-card-title>Beam Depth [mm]</v-card-title>
              <v-card-text>
                <connection-double-chart
                  :fields="[ConnectionField.DB, ConnectionField.Slab]"
                  :query="query"
                  :searches.sync="searches"
                ></connection-double-chart>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="6">
            <v-card>
              <v-card-title>Column Depth [mm]</v-card-title>
              <v-card-text>
                <connection-double-chart
                  :fields="[ConnectionField.DC, ConnectionField.NDp]"
                  :query="query"
                  :searches.sync="searches"
                ></connection-double-chart>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12">
            <v-card>
              <v-card-title>Steel Material</v-card-title>
              <v-card-text>
                <connection-single-chart
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
    <v-row>
      <v-col>
        <v-divider></v-divider>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <h1>Playground</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-text>
            <locale-select
              v-model="singleField"
              :items="fields"
              prefix="connection."
            ></locale-select>
            <connection-single-chart
              :field="singleField"
              :query="query"
              :searches.sync="searches"
            ></connection-single-chart>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col>
        <v-card>
          <v-card-text>
            <locale-select
              v-model="doubleFields[0]"
              :items="fields"
              prefix="connection."
            ></locale-select>
            <locale-select
              v-model="doubleFields[1]"
              :items="fields"
              prefix="connection."
            ></locale-select>
            <connection-double-chart
              :fields="doubleFields"
              :query="query"
              :searches.sync="searches"
            ></connection-double-chart>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from "vue-property-decorator";
import ConnectionTable from "@/components/connection/ConnectionTable.vue";
import LocaleSelect from "@/components/commons/LocaleSelect.vue";
import ConnectionSingleChart from "@/components/charts/ConnectionSingleChart.vue";
import ConnectionDoubleChart from "@/components/charts/ConnectionDoubleChart.vue";
import ConnectionParallelChart from "@/components/charts/ConnectionParallelChart.vue";
import { Searches } from "@/utils/common";
import { ConnectionField } from "@/backend";

@Component({
  components: {
    ConnectionTable,
    LocaleSelect,
    ConnectionSingleChart,
    ConnectionDoubleChart,
    ConnectionParallelChart,
  },
})
export default class ConnectionDashboard extends Vue {
  readonly ConnectionField = ConnectionField;
  readonly fields: string[] = Object.values(ConnectionField);
  readonly parallelFields: ConnectionField[] = [
    ConnectionField.DB,
    ConnectionField.DC,
    ConnectionField.NDp,
    ConnectionField.ConnectionType,
  ];

  search = "";
  searches: Searches = {};

  singleField = ConnectionField.Date;
  doubleFields: [ConnectionField, ConnectionField] = [
    ConnectionField.TCf,
    ConnectionField.TDpTot,
  ];

  get query(): string {
    const queries = Object.entries(this.searches)
      .filter(
        ([, value]) =>
          value != undefined && (typeof value == "boolean" || value.length > 0)
      )
      .map(([key, value]) => `${key}:${value}`);
    if (this.search && this.search.length > 0) {
      queries.push(`%${this.search}%`);
    }
    return queries.join(";");
  }
}
</script>
