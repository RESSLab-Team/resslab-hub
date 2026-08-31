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
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

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
  return props.connection.backing_bar
    ? t('detail.connection.backing_bar_kept')
    : t('detail.connection.backing_bar_removed')
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
          title: t('detail.connection.chart_subassembly_response'),
          xAxisName: t('detail.connection.axis_total_story_drift_angle'),
          yAxisName: t('detail.connection.axis_lateral_load')
        },
        {
          count: connection.global_west_count,
          promise: connectionsApi.getConnectionsGlobalWest(connection.id),
          title: t('detail.connection.chart_global_west'),
          xAxisName: t('detail.connection.axis_total_story_drift_angle'),
          yAxisName: t('detail.connection.axis_lateral_load')
        }
      ],
      [
        {
          count: connection.panel_zone_count,
          promise: connectionsApi.getConnectionsPanelZones(connection.id),
          title: t('detail.connection.chart_panel_zone_response'),
          xAxisName: t('detail.connection.axis_panel_zone_shear_distortion'),
          yAxisName: t('detail.connection.axis_panel_zone_shear_force')
        }
      ],
      [
        {
          count: connection.beam_count,
          promise: connectionsApi.getConnectionsBeam(connection.id),
          title:
            connection.beam_west_count > 0
              ? t('detail.connection.chart_east_beam')
              : t('detail.connection.chart_beam'),
          xAxisName: t('detail.connection.axis_chord_rotation'),
          yAxisName: t('detail.connection.axis_moment')
        },
        {
          count: connection.beam_west_count,
          promise: connectionsApi.getConnectionsBeamWest(connection.id),
          title: t('detail.connection.chart_west_beam'),
          xAxisName: t('detail.connection.axis_chord_rotation'),
          yAxisName: t('detail.connection.axis_moment')
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
    database-id="connections"
    :record="connection"
    :eyebrow="`${connection.connection_type}${$t('detail.connection.eyebrow_suffix')}`"
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
      <h3 class="cd-section-h">{{ $t('detail.connection.section_loading_geometric') }}</h3>
      <div class="cd-twocol">
        <div class="cd-prop-block">
          <property-item :name="$t('detail.connection.loading_protocol')">
            {{ connection.loading_protocol }}
          </property-item>
          <property-item :name="$t('detail.connection.structural_configuration')">
            {{ connection.specimen_type }}
          </property-item>
          <property-item :name="$t('detail.connection.connection_type')">
            {{ connection.connection_type }}
          </property-item>
          <property-item mono :name="$t('detail.connection.beam_cross_section')">
            {{ connection.section_b }}
          </property-item>
          <property-item mono :name="$t('detail.connection.column_cross_section')">
            {{ connection.section_c }}
          </property-item>
          <property-item
            v-if="connection.t_dp_tot"
            :name="$t('detail.connection.doubler_plate_thickness')"
            unit="mm"
          >
            {{ connection.t_dp_tot }}
          </property-item>
          <property-item :name="$t('detail.connection.weld_electrode')">
            {{ formatString(connection.electrode) }}
          </property-item>
          <property-item :name="$t('detail.connection.backing_bar')">
            {{ backingBar }}
          </property-item>
        </div>
        <div class="cd-schematic">
          <template v-if="connectionTypeImageSrc">
            <div class="cd-schematic-frame">
              <img :src="connectionTypeImageSrc" :alt="`${connection.connection_type} schematic`" />
            </div>
            <div class="cd-schematic-cap">
              {{ connection.connection_type }}
              {{ $t('detail.connection.caption_connection_schematic') }}
            </div>
          </template>
          <template v-if="specimenTypeImageSrc">
            <div class="cd-schematic-frame cd-schematic-frame-sm">
              <img :src="specimenTypeImageSrc" :alt="`${connection.specimen_type} schematic`" />
            </div>
            <div class="cd-schematic-cap">
              {{ connection.specimen_type }} {{ $t('detail.connection.caption_configuration') }}
            </div>
          </template>
        </div>
      </div>

      <template v-if="connection.slab">
        <h4 class="cd-section-h cd-section-h-sub">
          {{ $t('detail.connection.section_composite_slab') }}
        </h4>
        <div class="cd-prop-block cd-prop-block-row">
          <property-item :name="$t('detail.connection.deck_ribs_orientation')">
            {{ connection.deck_ribs_orientation }}
          </property-item>
          <property-item :name="$t('detail.connection.thickness')" unit="mm">
            {{ formatNumber(connection.h_t) }}
          </property-item>
          <property-item :name="$t('detail.connection.width')" unit="mm">
            {{ formatNumber(connection.w) }}
          </property-item>
          <property-item :name="$t('detail.connection.concrete_compressive_strength')" unit="MPa">
            {{ formatNumber(connection.f_cm, 1) }}
          </property-item>
        </div>
      </template>

      <h3 class="cd-section-h">{{ $t('detail.connection.section_steel_material_designation') }}</h3>
      <div class="cd-twocol">
        <div class="cd-prop-block">
          <div class="cd-prop-sub">{{ $t('detail.connection.sub_beam') }}</div>
          <property-item :name="$t('detail.connection.steel_type')">
            {{ connection.steel_b }}
          </property-item>
          <property-item :name="$t('detail.connection.nominal_yield_stress')" unit="MPa">
            {{ formatNumber(connection.f_yb) }}
          </property-item>
          <property-item :name="$t('detail.connection.measured_yield_stress_flange')" unit="MPa">
            {{ formatNumber(connection.f_ybf, 1) }}
          </property-item>
          <property-item :name="$t('detail.connection.measured_yield_stress_web')" unit="MPa">
            {{ formatNumber(connection.f_ybw, 1) }}
          </property-item>
        </div>
        <div class="cd-prop-block">
          <div class="cd-prop-sub">{{ $t('detail.connection.sub_column') }}</div>
          <property-item :name="$t('detail.connection.steel_type')">
            {{ connection.steel_c }}
          </property-item>
          <property-item :name="$t('detail.connection.nominal_yield_stress')" unit="MPa">
            {{ formatNumber(connection.f_yc) }}
          </property-item>
          <property-item :name="$t('detail.connection.measured_yield_stress_flange')" unit="MPa">
            {{ formatNumber(connection.f_ycf, 1) }}
          </property-item>
          <property-item :name="$t('detail.connection.measured_yield_stress_web')" unit="MPa">
            {{ formatNumber(connection.f_ycw, 1) }}
          </property-item>
        </div>
      </div>

      <h3 class="cd-section-h">{{ $t('detail.connection.section_panel_zone_strength_ratio') }}</h3>
      <div class="cd-kpi-grid">
        <div class="cd-kpi">
          <div class="cd-kpi-num">{{ formatNumber(connection.ru_rn_el_m, 2) }}</div>
          <div class="cd-kpi-lbl">Vpz,m / Rpz,el</div>
          <div class="cd-kpi-hint">
            {{ $t('detail.connection.kpi_hint_elastic_strength_reference') }}
          </div>
        </div>
        <div class="cd-kpi">
          <div class="cd-kpi-num">{{ formatNumber(connection.ru_rn_pl_m, 2) }}</div>
          <div class="cd-kpi-lbl">Vpz,m / Rpz,pl</div>
          <div class="cd-kpi-hint">
            {{ $t('detail.connection.kpi_hint_plastic_strength_reference') }}
          </div>
        </div>
        <div class="cd-kpi">
          <div class="cd-kpi-num">{{ formatNumber(connection.g_max_g_y, 2) }}</div>
          <div class="cd-kpi-lbl">γmax / γy</div>
          <div class="cd-kpi-hint">
            {{ $t('detail.connection.kpi_hint_panel_zone_ductility_demand') }}
          </div>
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
          {{ $t('detail.connection.view_publication') }}
        </a>
      </div>
    </template>
  </common-detail>
</template>
