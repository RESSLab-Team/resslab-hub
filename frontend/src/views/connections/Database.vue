<template>
  <v-row>
    <v-col cols="8">
      <connection-browser
        :search.sync="search"
        :searches.sync="searches"
        :query="query"
      ></connection-browser>
    </v-col>
    <v-col>
      <connection-chart
        :searches.sync="searches"
        :query="query"
      ></connection-chart>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from "vue-property-decorator";
import ConnectionBrowser from "@/components/ConnectionBrowser.vue";
import ConnectionChart from "@/components/ConnectionChart.vue";
import { Searches } from "@/utils/common";

@Component({
  components: {
    ConnectionBrowser,
    ConnectionChart,
  },
})
export default class Home extends Vue {
  search = "";
  searches: Searches = {};

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
