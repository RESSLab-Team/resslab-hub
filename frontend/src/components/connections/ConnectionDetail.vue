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
      <p>
        <property-item name="Publication">
          <a v-if="link" :href="link" target="_blank">
            {{ connection.reference }}
          </a>
          <span v-else>{{ connection.reference }}</span>
        </property-item>
      </p>
      <v-carousel
        v-if="carouselItemCount > 0"
        :height="chartHeight"
        hide-delimiters
        :show-arrows="carouselItemCount > 1"
      >
        <v-carousel-item v-if="hasGlobal">
          <simple-line-chart
            v-if="connection.global_count > 0"
            :color="color"
            :max-width="chartHeight"
            :promise="globalPromise"
            title="Global"
            x-axis-name="Total story drift angle [rad]"
            y-axis-name="Lateral load [kN]"
          ></simple-line-chart>
          <simple-line-chart
            v-if="connection.global_west_count > 0"
            :color="color"
            :max-width="chartHeight"
            :promise="globalWestPromise"
            title="Global West"
            x-axis-name="Total story drift angle [rad]"
            y-axis-name="Lateral load [kN]"
          ></simple-line-chart>
        </v-carousel-item>
        <v-carousel-item v-if="hasPanelZone">
          <simple-line-chart
            :color="color"
            :max-width="chartHeight"
            :promise="panelZonePromise"
            title="Panel Zone"
            x-axis-name="Panel zone shear distortion [rad]"
            y-axis-name="Panel zone shear force [kN]"
          ></simple-line-chart>
        </v-carousel-item>
      </v-carousel>
      <h2>Loading and geometric parameters</h2>
      <p>
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
          {{ connection.electrode | formatString }}
        </property-item>
        <property-item name="Backing bar">
          {{ backingBar }}
        </property-item>
      </p>
      <template v-if="connection.slab">
        <h2>Slab properties</h2>
        <p>
          <property-item name="Orientation of deck ribs">
            {{ connection.deck_ribs_orientation }}
          </property-item>
          <property-item name="Thickness" unit="mm">
            {{ connection.h_t | formatNumber() }}
          </property-item>
          <property-item name="Width" unit="mm">
            {{ connection.w | formatNumber() }}
          </property-item>
          <property-item name="Concrete compressive strength" unit="MPa">
            {{ connection.f_cm | formatNumber(1) }}
          </property-item>
        </p>
      </template>
      <h2>Steel material designation</h2>
      <v-row>
        <v-col>
          <h3>Beam</h3>
          <p>
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
          </p>
        </v-col>
        <v-col>
          <h3>Column</h3>
          <p>
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
          </p>
        </v-col>
      </v-row>
      <h2>Panel zone strength ratio</h2>
      <p>
        <property-item name="Vpz,m/Rpz,el">
          {{ connection.ru_rn_el_m | formatNumber(2) }}
        </property-item>
        <property-item name="Vpz,m/Rpz,pl">
          {{ connection.ru_rn_pl_m | formatNumber(2) }}
        </property-item>
      </p>
    </v-card-text>
  </v-card>
</template>

<style lang="scss">
.v-carousel__item > .v-responsive__content {
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
        return "Not Applicable";
      } else if (isNaN(value)) {
        return "Not Reported";
      } else {
        return value.toFixed(fractionDigits);
      }
    },
    formatString: function (value: string | null): string {
      if (value === null) {
        return "Not Applicable";
      } else if (value === "NR") {
        return "Not Reported";
      } else {
        return value;
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
  readonly chartHeight = 300;

  @Prop(Object)
  readonly connection!: ConnectionModel;

  get hasGlobal(): boolean {
    return this.connection.global_count + this.connection.global_west_count > 0;
  }

  get hasPanelZone(): boolean {
    return this.connection.panel_zone_count > 0;
  }

  get carouselItemCount(): number {
    return [this.hasGlobal, this.hasPanelZone].filter((v) => v).length;
  }

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

  get link(): string | undefined {
    const matches: string[] | null =
      this.connection.reference.match(/\bhttps?:\/\/\S+/gi);
    const link: string | undefined = matches ? matches[0] : undefined;
    return link?.replace(/\.$/, "");
  }

  onClose(): void {
    this.$emit("close");
  }
}
</script>
