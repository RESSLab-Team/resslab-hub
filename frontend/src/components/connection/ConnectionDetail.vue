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
        <v-col cols="12">
          <v-expansion-panels accordion hover multiple>
            <v-expansion-panel v-if="connection.global_count > 0">
              <v-expansion-panel-header>Global</v-expansion-panel-header>
              <v-expansion-panel-content>
                <simple-line-chart
                  :color="color"
                  :promise="globalPromise"
                  x-axis-name="Total story drift angle [rad]"
                  y-axis-name="Lateral load [kN]"
                ></simple-line-chart>
              </v-expansion-panel-content>
            </v-expansion-panel>
            <v-expansion-panel v-if="connection.global_west_count > 0">
              <v-expansion-panel-header>Global West</v-expansion-panel-header>
              <v-expansion-panel-content>
                <simple-line-chart
                  :color="color"
                  :promise="globalWestPromise"
                  x-axis-name="Total story drift angle [rad]"
                  y-axis-name="Lateral load [kN]"
                ></simple-line-chart>
              </v-expansion-panel-content>
            </v-expansion-panel>
            <v-expansion-panel v-if="connection.panel_zone_count > 0">
              <v-expansion-panel-header>Panel Zone</v-expansion-panel-header>
              <v-expansion-panel-content>
                <simple-line-chart
                  :color="color"
                  :promise="panelZonePromise"
                  x-axis-name="Panel zone shear distortion [rad]"
                  y-axis-name="Panel zone shear force [kN]"
                ></simple-line-chart>
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
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
            {{ connection.f_yb | formatNumber(0) }}
          </property-item>
          <property-item name="Measured yield stress (flange)" unit="MPa">
            {{ connection.f_ybf | formatNumber(1) }}
          </property-item>
          <property-item name="Measured yield stress (web)" unit="MPa">
            {{ connection.f_ybw | formatNumber(1) }}
          </property-item>
        </v-col>
        <v-col>
          <h3>Column</h3>
          <property-item name="Steel type">
            {{ connection.steel_c }}
          </property-item>
          <property-item name="Nominal yield stress" unit="MPa">
            {{ connection.f_yc | formatNumber(0) }}
          </property-item>
          <property-item name="Measured yield stress (flange)" unit="MPa">
            {{ connection.f_ycf | formatNumber(1) }}
          </property-item>
          <property-item name="Measured yield stress (web)" unit="MPa">
            {{ connection.f_ycw | formatNumber(1) }}
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

<style lang="scss">
.v-expansion-panel-content__wrap {
  display: flex;
  justify-content: center;
}
</style>

<script lang="ts">
import { ConnectionModel } from "@/backend";
import SimpleLineChart from "@/components/commons/charts/SimpleLineChart.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { AxiosResponse } from "axios";
import { Component, Prop, Vue } from "vue-property-decorator";
import colors from "vuetify/lib/util/colors";

@Component({
  components: {
    SimpleLineChart,
    PropertyItem,
  },
  filters: {
    formatNumber: function (
      value: number | null,
      fractionDigits: number | undefined
    ): string {
      if (value === null) {
        return "Not Reported";
      } else {
        return value.toFixed(fractionDigits);
      }
    },
  },
})
export default class ConnectionDetail extends Vue {
  readonly color = colors.red;
  readonly chartBind = {
    cols: "12",
    sm: "6",
    md: "12",
    lg: "6",
    xl: "4",
  };

  @Prop(Object)
  readonly connection!: ConnectionModel;

  get globalPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$connectionsApi.getConnectionsGlobals(this.connection.id);
  }

  get globalWestPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$connectionsApi.getConnectionsGlobalWest(this.connection.id);
  }

  get panelZonePromise(): Promise<AxiosResponse<number[][]>> {
    return this.$connectionsApi.getConnectionsPanelZones(this.connection.id);
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
