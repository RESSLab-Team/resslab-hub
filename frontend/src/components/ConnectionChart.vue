<template>
  <div>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>Connection Type</v-card-title>
          <v-card-text>
            <connection-single-chart
              :field="ConnectionField.ConnectionType"
              :query="query"
              :searches.sync="fieldSearches"
            ></connection-single-chart>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>Beam Depth</v-card-title>
          <v-card-text>
            <connection-double-chart
              :fields="[ConnectionField.DB, ConnectionField.Slab]"
              :query="query"
              :searches.sync="fieldSearches"
            ></connection-double-chart>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>Column Depth</v-card-title>
          <v-card-text>
            <connection-double-chart
              :fields="[ConnectionField.DC, ConnectionField.NDp]"
              :query="query"
              :searches.sync="fieldSearches"
            ></connection-double-chart>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col>
        <v-card>
          <v-card-title>Steel Material</v-card-title>
          <v-card-text>
            <connection-single-chart
              :field="ConnectionField.SteelB"
              :query="query"
              :searches.sync="fieldSearches"
            ></connection-single-chart>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";
import { ConnectionField } from "@/backend";
import { Searches } from "@/utils/common";
import ConnectionSingleChart from "@/components/charts/ConnectionSingleChart.vue";
import ConnectionDoubleChart from "@/components/charts/ConnectionDoubleChart.vue";

@Component({
  components: {
    ConnectionSingleChart,
    ConnectionDoubleChart,
  },
})
export default class ConnectionChart extends Vue {
  readonly ConnectionField = ConnectionField;

  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  fieldSearches!: Searches;
  @Prop({ type: String, default: "" })
  readonly query!: string;
}
</script>
