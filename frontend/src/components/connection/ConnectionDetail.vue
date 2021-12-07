<template>
  <v-row>
    <v-col cols="6">
      <v-card>
        <v-card-title>Global</v-card-title>
        <simple-line-chart
          :promise="globalPromise"
          x-axis-name="Total story drift angle (rad)"
          y-axis-name="Force in the actuator (kN)"
        ></simple-line-chart>
      </v-card>
    </v-col>
    <v-col cols="6">
      <v-card>
        <v-card-title>Panel Zone</v-card-title>
        <simple-line-chart
          :color="colors.red"
          :promise="panelZonePromise"
          x-axis-name="Panel zone shear distortion (rad)"
          y-axis-name="Panel zone shear force (kN)"
        ></simple-line-chart>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue, Prop } from "vue-property-decorator";
import colors from "vuetify/lib/util/colors";
import SimpleLineChart from "@/components/charts/SimpleLineChart.vue";
import { AxiosResponse } from "axios";

@Component({
  components: {
    SimpleLineChart,
  },
})
export default class ConnectionDetail extends Vue {
  readonly colors = colors;

  @Prop(String)
  readonly connectionId!: string;

  get globalPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$connectionsApi.getGlobals(this.connectionId);
  }

  get panelZonePromise(): Promise<AxiosResponse<number[][]>> {
    return this.$connectionsApi.getPanelZones(this.connectionId);
  }
}
</script>
