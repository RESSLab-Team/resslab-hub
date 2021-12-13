<template>
  <v-card>
    <v-card-title>
      {{ connection.experimental_program }} ({{ connection.date }}) -
      {{ connection.specimen_designation }}
      <v-spacer></v-spacer>
      <v-btn color="primary" text @click="onClose">
        <v-icon>mdi-close</v-icon>
        Close
      </v-btn>
    </v-card-title>
    <v-card-text>
      <property-item name="Publication">TODO</property-item>
    </v-card-text>
    <v-card-text
      v-if="connection.global_count > 0 || connection.panel_zone_count > 0"
    >
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
    <v-card-text>
      <h2>Loading and geometric parameters</h2>
      <property-item name="Loading protocol">
        {{ connection.loading_protocol }}
      </property-item>
      <property-item name="Structural configuration">
        {{ connection.specimen_type }}
      </property-item>
      <property-item name="Connection type">
        {{ connection.connection_type }}
      </property-item>
      <property-item name="Beam cross section">
        {{ connection.section_b }}
      </property-item>
      <property-item name="Column cross section">
        {{ connection.section_c }}
      </property-item>
      <property-item
        v-if="connection.t_dp_tot"
        name="Doubler plate thickness"
        unit="mm"
      >
        {{ connection.t_dp_tot }}
      </property-item>
      <property-item name="Beam flange-to-column flange weld electrode">
        {{ connection.weld_electrode_type }}
      </property-item>
      <property-item name="Backing bar">
        {{ backingBar }}
      </property-item>
    </v-card-text>
    <v-card-text v-if="connection.slab">
      <h2>Slab properties</h2>
      <property-item name="Orientation of deck ribs">TODO</property-item>
      <property-item name="Thickness" unit="mm">
        {{ connection.ht }}
      </property-item>
      <property-item name="Width" unit="mm">
        {{ connection.w }}
      </property-item>
      <property-item name="Concrete compressive strength" unit="MPa">
        {{ connection.fc }}
      </property-item>
    </v-card-text>
    <v-card-text>
      <h2>Steel material designation</h2>
      <v-row>
        <v-col>
          <h3>Beam</h3>
          <property-item name="Steel type">
            {{ connection.steel_b }}
          </property-item>
          <property-item name="Nominal yield stress" unit="MPa">
            TODO
          </property-item>
          <property-item name="Measured yield stress_flange" unit="MPa">
            TODO
          </property-item>
          <property-item name="Measured yield stress_web" unit="MPa">
            TODO
          </property-item>
        </v-col>
        <v-col>
          <h3>Column</h3>
          <property-item name="Steel type">
            {{ connection.steel_c }}
          </property-item>
          <property-item name="Nominal yield stress" unit="MPa">
            TODO
          </property-item>
          <property-item name="Measured yield stress_flange" unit="MPa">
            TODO
          </property-item>
          <property-item name="Measured yield stress_web" unit="MPa">
            TODO
          </property-item>
        </v-col>
      </v-row>
    </v-card-text>
    <v-card-text>
      <h2>Design parameters</h2>
      <property-item name="Panel zone strength ratio">TODO</property-item>
      <property-item name="Vpz,m/Rpz,el">TODO</property-item>
      <property-item name="Vpz,m/Rpz,pl">TODO</property-item>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { ConnectionModel } from "@/backend";
import SimpleLineChart from "@/components/charts/SimpleLineChart.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { AxiosResponse } from "axios";
import { Component, Prop, Vue } from "vue-property-decorator";
import colors from "vuetify/lib/util/colors";

@Component({
  components: {
    SimpleLineChart,
    PropertyItem,
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

  get backingBar(): string {
    if (this.connection.backing_bar === null) {
      return "";
    }
    return this.connection.backing_bar ? "kept in place" : "removed";
  }

  onClose(): void {
    this.$emit("close");
  }
}
</script>
