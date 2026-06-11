<script setup lang="ts">
import type { ConnectionModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { connectionsApi } from '@/plugins/axios'
import { publicPath } from '@/utils/common'
import { getConnectionSpecimenImage } from '@/utils/component'
import { formatNumber, formatString } from '@/utils/formatter'
import { mdiOpenInNew } from '@mdi/js'
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

const connectionTypeImageSrc = computed<string>(() =>
  props.connection.connection_type
    ? `${publicPath}img/connection-type/${props.connection.connection_type.toLowerCase()}.svg`
    : ''
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
    :eyebrow="`${connection.connection_type} · Connection`"
    :specimen-id="connection.specimen_designation"
    :reference="connection.reference"
    :link="connection.link"
    :carousel-items="carouselItems"
    @close="emit('close')"
  >
    <template #title>
      {{ connection.experimental_program }}
      <span class="cd-title-year">({{ connection.date }})</span>
    </template>
    <template #body>
      <h3 class="cd-section-h">Loading &amp; geometric parameters</h3>
      <div class="cd-twocol">
        <div class="cd-prop-block">
          <property-item name="Loading protocol">
            {{ connection.loading_protocol }}
          </property-item>
          <property-item name="Structural configuration">
            {{ connection.specimen_type }}
          </property-item>
          <property-item name="Connection type">
            {{ connection.connection_type }}
          </property-item>
          <property-item mono name="Beam cross section">
            {{ connection.section_b }}
          </property-item>
          <property-item mono name="Column cross section">
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
        </div>
        <div class="cd-schematic">
          <template v-if="connectionTypeImageSrc">
            <div class="cd-schematic-frame">
              <img :src="connectionTypeImageSrc" :alt="`${connection.connection_type} schematic`" />
            </div>
            <div class="cd-schematic-cap">
              {{ connection.connection_type }} connection schematic
            </div>
          </template>
          <template v-if="specimenTypeImageSrc">
            <div class="cd-schematic-frame cd-schematic-frame-sm">
              <img :src="specimenTypeImageSrc" :alt="`${connection.specimen_type} schematic`" />
            </div>
            <div class="cd-schematic-cap">{{ connection.specimen_type }} configuration</div>
          </template>
        </div>
      </div>

      <template v-if="connection.slab">
        <h4 class="cd-section-h cd-section-h-sub">Composite slab</h4>
        <div class="cd-prop-block cd-prop-block-row">
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
        </div>
      </template>

      <h3 class="cd-section-h">Steel material designation</h3>
      <div class="cd-twocol">
        <div class="cd-prop-block">
          <div class="cd-prop-sub">Beam</div>
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
        </div>
        <div class="cd-prop-block">
          <div class="cd-prop-sub">Column</div>
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
        </div>
      </div>

      <h3 class="cd-section-h">Panel-zone strength ratio</h3>
      <div class="cd-kpi-grid">
        <div class="cd-kpi">
          <div class="cd-kpi-num">{{ formatNumber(connection.ru_rn_el_m, 2) }}</div>
          <div class="cd-kpi-lbl">Vpz,m / Rpz,el</div>
          <div class="cd-kpi-hint">Elastic strength reference</div>
        </div>
        <div class="cd-kpi">
          <div class="cd-kpi-num">{{ formatNumber(connection.ru_rn_pl_m, 2) }}</div>
          <div class="cd-kpi-lbl">Vpz,m / Rpz,pl</div>
          <div class="cd-kpi-hint">Plastic strength reference</div>
        </div>
        <div class="cd-kpi">
          <div class="cd-kpi-num">{{ formatNumber(connection.g_max_g_y, 2) }}</div>
          <div class="cd-kpi-lbl">γmax / γy</div>
          <div class="cd-kpi-hint">Panel-zone ductility demand</div>
        </div>
      </div>

      <div v-if="connection.link" class="cd-foot">
        <a
          class="btn btn-secondary btn-sm"
          :href="connection.link"
          target="_blank"
          rel="noreferrer"
        >
          <v-icon :icon="mdiOpenInNew" size="12" />
          View publication
        </a>
      </div>
    </template>
  </common-detail>
</template>
