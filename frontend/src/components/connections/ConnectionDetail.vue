<template>
  <common-detail
    :reference="reference"
    :link="link"
    :carousel-items="carouselItems"
    @close="close"
  >
    <template #title>
      {{ connection.experimental_program }} ({{ connection.date }}) -
      {{ connection.specimen_designation }}
    </template>
    <template #parameters>
      <v-row>
        <v-col cols="6">
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
        </v-col>
        <v-col v-if="specimenTypeImageSrc" cols="6">
          <v-img contain :src="specimenTypeImageSrc" max-height="160"></v-img>
        </v-col>
      </v-row>
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
    </template>
    <template #designation>
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
    </template>
  </common-detail>
</template>

<script lang="ts">
import { ConnectionModel } from "@/backend";
import CommonDetail from "@/components/commons/CommonDetail.vue";
import CommonDetailMixin from "@/components/commons/CommonDetailMixin.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { getConnectionSpecimenImage } from "@/utils/component";
import { CarouselItem } from "@/utils/detail";
import { AxiosResponse } from "axios";
import { Component, VModel } from "vue-property-decorator";

@Component({
  components: {
    CommonDetail,
    PropertyItem,
  },
})
export default class ConnectionDetail extends CommonDetailMixin {
  @VModel({ type: Object as () => ConnectionModel })
  readonly connection!: ConnectionModel;

  get reference(): string {
    return this.connection.reference;
  }

  get link(): string | undefined {
    return this.connection.link;
  }

  get carouselItems(): CarouselItem[][] {
    return [
      this.connection.global_count > 0 || this.connection.global_west_count > 0
        ? [
            {
              hidden: this.connection.global_count === 0,
              promise: this.globalPromise,
              title: "Subassembly Response",
              xAxisName: "Total story drift angle [rad]",
              yAxisName: "Lateral load [kN]",
            },
            {
              hidden: this.connection.global_west_count === 0,
              promise: this.globalWestPromise,
              title: "Global West",
              xAxisName: "Total story drift angle [rad]",
              yAxisName: "Lateral load [kN]",
            },
          ]
        : [],
      this.connection.panel_zone_count > 0
        ? [
            {
              promise: this.panelZonePromise,
              title: "Panel Zone Response",
              xAxisName: "Panel zone shear distortion [rad]",
              yAxisName: "Panel zone shear force [kN]",
            },
          ]
        : [],
      this.connection.beam_count > 0 || this.connection.beam_west_count > 0
        ? [
            {
              hidden: this.connection.beam_count === 0,
              promise: this.beamPromise,
              title: this.connection.beam_west_count > 0 ? "East Beam" : "Beam",
              xAxisName: "Chord Rotation [rads]",
              yAxisName: "Moment [kN-mm]",
            },
            {
              hidden: this.connection.beam_west_count === 0,
              promise: this.beamWestPromise,
              title: "West Beam",
              xAxisName: "Chord Rotation [rads]",
              yAxisName: "Moment [kN-mm]",
            },
          ]
        : [],
    ].filter((item) => item.length > 0);
  }

  get beamPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$connectionsApi.getConnectionsBeam(this.connection.id);
  }

  get beamWestPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$connectionsApi.getConnectionsBeamWest(this.connection.id);
  }

  get globalPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$connectionsApi.getConnectionsGlobal(this.connection.id);
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

  get specimenTypeImageSrc(): string {
    return getConnectionSpecimenImage(this.connection.specimen_type);
  }
}
</script>
