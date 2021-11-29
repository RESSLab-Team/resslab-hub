<template>
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
        :searches.sync="fieldSearches"
      ></connection-single-chart>
    </v-card-text>
    <v-divider></v-divider>
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
        :searches.sync="fieldSearches"
      ></connection-double-chart>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";
import { ConnectionField } from "@/backend";
import { Searches } from "@/utils/common";
import LocaleSelect from "@/components/commons/LocaleSelect.vue";
import ConnectionSingleChart from "@/components/charts/ConnectionSingleChart.vue";
import ConnectionDoubleChart from "@/components/charts/ConnectionDoubleChart.vue";

@Component({
  components: {
    LocaleSelect,
    ConnectionSingleChart,
    ConnectionDoubleChart,
  },
})
export default class ConnectionChart extends Vue {
  readonly fields: string[] = Object.values(ConnectionField);

  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  fieldSearches!: Searches;
  @Prop({ type: String, default: "" })
  readonly query!: string;

  singleField = ConnectionField.ConnectionType;
  doubleFields: [ConnectionField, ConnectionField] = [
    ConnectionField.DC,
    ConnectionField.NDp,
  ];
}
</script>
