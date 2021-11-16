<template>
  <v-row>
    <v-col cols="8">
      <connection-browser></connection-browser>
    </v-col>
    <v-col>
      <connection-chart></connection-chart>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from "vue-property-decorator";
import ConnectionBrowser from "@/components/ConnectionBrowser.vue";
import ConnectionChart from "@/components/ConnectionChart.vue";

@Component({
  components: {
    ConnectionBrowser,
    ConnectionChart,
  },
})
export default class Home extends Vue {}
</script>
