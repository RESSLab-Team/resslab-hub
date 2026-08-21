<script setup lang="ts">
import type { BraceModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { bracesApi } from '@/plugins/axios'
import { publicPath } from '@/utils/common'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

const props = defineProps<{
  brace: BraceModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const carouselItems = ref<DetailCarouselItem[][]>([])

const isGussetPlate = computed<boolean>(() => props.brace.boundary_condition === 'Gusset plate')

const imageTypeSrc = computed<string | undefined>(() => {
  switch (props.brace.boundary_condition) {
    case 'Gusset plate':
      return publicPath + 'img/brace/type/gusset-plate.png'
    case 'Pin-Pin end':
      return publicPath + 'img/brace/type/pinned-end.png'
    case 'Fixed-fixed end':
      return publicPath + 'img/brace/type/fixed-end.png'
    case 'Fixed_pinned end':
      return publicPath + 'img/brace/type/fixed-pinned.png'
  }
  return undefined
})

watch(
  () => props.brace,
  (brace) => {
    carouselItems.value = [
      [
        {
          count: brace.displacement_count,
          promise: bracesApi.getBracesDisplacement(brace.id),
          title: t('detail.brace.chart_force_displacement'),
          xAxisName: t('detail.brace.axis_displacement'),
          yAxisName: t('detail.brace.axis_force')
        }
      ]
    ]
  },
  {
    immediate: true
  }
)

function formatNumber(value?: number | null) {
  return value ?? t('detail.brace.not_reported')
}
function formatString(value?: string | null): string {
  if (value == null) {
    return t('detail.brace.no')
  } else if (value === 'NR') {
    return t('detail.brace.not_reported')
  } else {
    return value
  }
}
</script>

<template>
  <common-detail
    database-id="braces"
    :record="brace"
    :reference="brace.reference"
    :link="brace.link"
    :carousel-items="carouselItems"
    @close="emit('close')"
  >
    <template #title>
      {{ brace.investigator }} ({{ brace.date }}) -
      {{ brace.specimen_ID }}
    </template>
    <template #body>
      <v-row>
        <v-col cols="6">
          <v-row>
            <v-col>
              <h2>{{ $t('detail.brace.section_loading_geometric') }}</h2>
              <property-item :name="$t('detail.brace.loading_protocol')">
                {{ brace.loading_protocol }}
              </property-item>
              <property-item :name="$t('detail.brace.brace_boundary_conditions')">
                {{ brace.boundary_condition }}
              </property-item>
              <property-item :name="$t('detail.brace.brace_cross_section_shape')">
                {{ brace.cross_section_shape }}
              </property-item>
              <property-item :name="$t('detail.brace.brace_cross_section_size')">
                {{ brace.cross_section_size }}
              </property-item>
              <property-item :name="$t('detail.brace.member_slenderness_ratio')">
                {{ brace.kl_r }}
              </property-item>
              <template v-if="isGussetPlate">
                <property-item :name="$t('detail.brace.gusset_plate_thickness')" unit="mm">
                  {{ brace.t_t }}
                </property-item>
                <property-item :name="$t('detail.brace.reinforcement_plate')">
                  {{ formatString(brace.reinforcement_pl) }}
                </property-item>
              </template>
            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <h2>{{ $t('detail.brace.section_steel_material_designation') }}</h2>
              <h3>{{ $t('detail.brace.sub_brace') }}</h3>
              <property-item :name="$t('detail.brace.steel_type')">
                {{ brace.steel }}
              </property-item>
              <property-item :name="$t('detail.brace.nominal_yield_stress')" unit="MPa">
                {{ formatNumber(brace.f_yn) }}
              </property-item>
              <property-item :name="$t('detail.brace.measured_yield_stress')" unit="MPa">
                {{ formatNumber(brace.fy_m) }}
              </property-item>
              <property-item :name="$t('detail.brace.ultimate_tensile_stress')" unit="MPa">
                {{ formatNumber(brace.f_um) }}
              </property-item>
              <h3>{{ $t('detail.brace.sub_gusset_plate') }}</h3>
              <template v-if="isGussetPlate">
                <property-item :name="$t('detail.brace.steel_type')">
                  {{ brace.steel_gp }}
                </property-item>
                <property-item :name="$t('detail.brace.nominal_yield_stress')" unit="MPa">
                  {{ formatNumber(brace.f_yn_gp) }}
                </property-item>
                <property-item :name="$t('detail.brace.measured_yield_stress')" unit="MPa">
                  {{ formatNumber(brace.f_ym_gp) }}
                </property-item>
                <property-item :name="$t('detail.brace.ultimate_tensile_stress')" unit="MPa">
                  {{ formatNumber(brace.f_um_gp) }}
                </property-item>
              </template>
              <template v-else>{{ $t('detail.brace.no_gusset_plates') }}</template>
            </v-col>
          </v-row>
        </v-col>
        <v-col cols="6">
          <v-img :src="imageTypeSrc" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
