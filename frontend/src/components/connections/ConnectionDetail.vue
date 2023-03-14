<script setup lang="ts">
import type { ConnectionModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { connectionsApi } from '@/plugins/axios'
import { getConnectionSpecimenImage } from '@/utils/component'
import { formatNumber, formatString } from '@/utils/formatter'
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  connection: ConnectionModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const carouselItems = ref<DetailCarouselItem[][]>([])

const backingBar = computed<string>(() => {
  if (props.connection.backing_bar === null) {
    return ''
  }
  return props.connection.backing_bar ? 'kept in place' : 'removed'
})

const specimenTypeImageSrc = computed<string>(() =>
  getConnectionSpecimenImage(props.connection.specimen_type)
)

watch(
  () => props.connection,
  (connection) => {
    carouselItems.value = [
      [
        {
          count: connection.global_count,
          promise: connectionsApi.getConnectionsGlobal(connection.id),
          title: 'Subassembly Response',
          xAxisName: 'Total story drift angle [rad]',
          yAxisName: 'Lateral load [kN]'
        },
        {
          count: connection.global_west_count,
          promise: connectionsApi.getConnectionsGlobalWest(connection.id),
          title: 'Global West',
          xAxisName: 'Total story drift angle [rad]',
          yAxisName: 'Lateral load [kN]'
        }
      ],
      [
        {
          count: connection.panel_zone_count,
          promise: connectionsApi.getConnectionsPanelZones(connection.id),
          title: 'Panel Zone Response',
          xAxisName: 'Panel zone shear distortion [rad]',
          yAxisName: 'Panel zone shear force [kN]'
        }
      ],
      [
        {
          count: connection.beam_count,
          promise: connectionsApi.getConnectionsBeam(connection.id),
          title: connection.beam_west_count > 0 ? 'East Beam' : 'Beam',
          xAxisName: 'Chord Rotation [rads]',
          yAxisName: 'Moment [kN-mm]'
        },
        {
          count: connection.beam_west_count,
          promise: connectionsApi.getConnectionsBeamWest(connection.id),
          title: 'West Beam',
          xAxisName: 'Chord Rotation [rads]',
          yAxisName: 'Moment [kN-mm]'
        }
      ]
    ]
  },
  {
    immediate: true
  }
)
</script>

<template>
  <common-detail
    :reference="connection.reference"
    :link="connection.link"
    :carousel-items="carouselItems"
    @close="emit('close')"
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
            <property-item v-if="connection.t_dp_tot" name="Doubler plate thickness" unit="mm">
              {{ connection.t_dp_tot }}
            </property-item>
            <property-item name="Beam flange-to-column flange weld electrode">
              {{ formatString(connection.electrode) }}
            </property-item>
            <property-item name="Backing bar">
              {{ backingBar }}
            </property-item>
          </p>
        </v-col>
        <v-col v-if="specimenTypeImageSrc" cols="6">
          <v-img contain :src="specimenTypeImageSrc" max-height="160" />
        </v-col>
      </v-row>
      <template v-if="connection.slab">
        <h2>Slab properties</h2>
        <p>
          <property-item name="Orientation of deck ribs">
            {{ connection.deck_ribs_orientation }}
          </property-item>
          <property-item name="Thickness" unit="mm">
            {{ formatNumber(connection.h_t) }}
          </property-item>
          <property-item name="Width" unit="mm">
            {{ formatNumber(connection.w) }}
          </property-item>
          <property-item name="Concrete compressive strength" unit="MPa">
            {{ formatNumber(connection.f_cm, 1) }}
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
              {{ formatNumber(connection.f_yb) }}
            </property-item>
            <property-item name="Measured yield stress (flange)" unit="MPa">
              {{ formatNumber(connection.f_ybf, 1) }}
            </property-item>
            <property-item name="Measured yield stress (web)" unit="MPa">
              {{ formatNumber(connection.f_ybw, 1) }}
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
              {{ formatNumber(connection.f_yc) }}
            </property-item>
            <property-item name="Measured yield stress (flange)" unit="MPa">
              {{ formatNumber(connection.f_ycf, 1) }}
            </property-item>
            <property-item name="Measured yield stress (web)" unit="MPa">
              {{ formatNumber(connection.f_ycw, 1) }}
            </property-item>
          </p>
        </v-col>
      </v-row>
      <h2>Panel Zone Strength Ratio</h2>
      <p>
        <property-item name="Vpz,m/Rpz,el">
          {{ formatNumber(connection.ru_rn_el_m, 2) }}
        </property-item>
        <property-item name="Vpz,m/Rpz,pl">
          {{ formatNumber(connection.ru_rn_pl_m, 2) }}
        </property-item>
      </p>
    </template>
  </common-detail>
</template>
