<template>
  <div>
    <v-row>
      <v-col cols="6">
        <v-row>
          <v-col>
            <connection-browser
              :search.sync="search"
              :searches.sync="searches"
              :query="query"
            ></connection-browser>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-card>
              <v-card-title> Parallel Axis </v-card-title>
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
        <connection-chart
          :searches.sync="searches"
          :query="query"
        ></connection-chart>
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
import ConnectionBrowser from "@/components/ConnectionBrowser.vue";
import ConnectionChart from "@/components/ConnectionChart.vue";
import LocaleSelect from "@/components/commons/LocaleSelect.vue";
import ConnectionSingleChart from "@/components/charts/ConnectionSingleChart.vue";
import ConnectionDoubleChart from "@/components/charts/ConnectionDoubleChart.vue";
import ConnectionParallelChart from "@/components/charts/ConnectionParallelChart.vue";
import { Searches } from "@/utils/common";
import { ConnectionField } from "@/backend";

@Component({
  components: {
    ConnectionBrowser,
    ConnectionChart,
    LocaleSelect,
    ConnectionSingleChart,
    ConnectionDoubleChart,
    ConnectionParallelChart,
  },
})
export default class Home extends Vue {
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
