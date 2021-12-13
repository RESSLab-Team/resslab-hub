<template>
  <v-card>
    <v-card-title>
      Available digitized data :
      {{ connection.experimental_program }} ({{ connection.date }}) -
      {{ connection.specimen_designation }}
      <v-spacer></v-spacer>
      <v-btn color="primary" text @click="onClose">
        <v-icon>mdi-close</v-icon>
        Close
      </v-btn>
    </v-card-title>
    <v-card-text>
      <v-row>
        <v-col v-if="connection.global_count > 0" cols="6">
          <v-card>
            <v-card-title>Global</v-card-title>
            <simple-line-chart
              :promise="globalPromise"
              x-axis-name="Total story drift angle (rad)"
              y-axis-name="Force in the actuator (kN)"
            ></simple-line-chart>
          </v-card>
        </v-col>
        <v-col v-if="connection.panel_zone_count > 0" cols="6">
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
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { ConnectionModel } from "@/backend";
import SimpleLineChart from "@/components/charts/SimpleLineChart.vue";
import { AxiosResponse } from "axios";
import { Component, Prop, Vue } from "vue-property-decorator";
import colors from "vuetify/lib/util/colors";

@Component({
  components: {
    SimpleLineChart,
  },
})
export default class ConnectionDetail extends Vue {
  readonly colors = colors;

  @Prop(Object)
  readonly connection!: ConnectionModel;

  get globalPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$connectionsApi.getGlobals(this.connection.id);
  }

  get panelZonePromise(): Promise<AxiosResponse<number[][]>> {
    return this.$connectionsApi.getPanelZones(this.connection.id);
  }

  onClose(): void {
    this.$emit("close");
  }
}
</script>
