<script setup lang="ts">
import type { ColumnModel } from '@/backend'
import CommonDetail, { type DetailCarouselItem } from '@/components/commons/CommonDetail.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import ZoomableImage from '@/components/commons/ZoomableImage.vue'
import { columnsApi } from '@/plugins/axios'
import { getColumnImage } from '@/utils/component'
import { formatNumber } from '@/utils/formatter'
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })

const props = defineProps<{
  column: ColumnModel
}>()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const carouselItems = ref<DetailCarouselItem[][]>([])

const imageSrc = computed<string | undefined>(() =>
  getColumnImage(
    props.column.axis_of_bending,
    props.column.boundary_condition,
    props.column.direction_lp
  )
)

watch(
  () => props.column,
  (column) => {
    carouselItems.value = [
      [
        {
          count: column.axial_shortening_count,
          promise: columnsApi.getColumnsAxialShortening(column.id),
          title: t('detail.column.chart_axial_shortening'),
          xAxisName: t('detail.column.axis_chord_rotation'),
          yAxisName: t('detail.column.axis_axial_shortening')
        }
      ],
      [
        {
          count: column.moment_strong_count,
          promise: columnsApi.getColumnsMomentStrong(column.id),
          title: t('detail.column.chart_moment_rotation'),
          xAxisName: t('detail.column.axis_chord_rotation'),
          yAxisName: t('detail.column.axis_moment')
        },
        {
          count: column.moment_weak_count,
          promise: columnsApi.getColumnsMomentWeak(column.id),
          title: t('detail.column.chart_moment_weak'),
          xAxisName: t('detail.column.axis_chord_rotation'),
          yAxisName: t('detail.column.axis_moment')
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
    database-id="columns"
    :record="column"
    :reference="column.reference"
    :link="column.link"
    :carousel-items="carouselItems"
    @close="emit('close')"
  >
    <template #title>
      {{ column.experimental_program }} - ({{ column.date }}) -
      {{ column.specimen_designation }}
    </template>
    <template #parameters>
      <v-row>
        <v-col cols="12" sm="6">
          <property-item column="lateral_lp" :name="$t('detail.column.loading_protocol')">
            {{ column.lateral_lp }}
          </property-item>
          <property-item :name="$t('detail.column.axial_load_ratio')">
            {{ column.axial_lp }} (Pg/Py = {{ column.p_g_over_p_ym }})
          </property-item>
          <property-item column="axis_of_bending" :name="$t('detail.column.axis_of_bending')">
            {{ column.axis_of_bending }}
          </property-item>
          <property-item
            column="boundary_condition"
            :name="$t('detail.column.boundary_conditions')"
          >
            {{ column.boundary_condition }}
          </property-item>
          <property-item column="section_c" :name="$t('detail.column.column_cross_section')">
            {{ column.section_c }}
          </property-item>
          <property-item
            column="l_b_over_r_yc"
            :name="$t('detail.column.member_slenderness_ratio')"
          >
            {{ formatNumber(column, 'l_b_over_r_yc', 1) }}
          </property-item>
        </v-col>
        <v-col cols="12" sm="6">
          <zoomable-image
            v-if="imageSrc"
            :src="imageSrc"
            :alt="$t('detail.column.figure_alt')"
            :max-height="256"
          />
        </v-col>
      </v-row>
    </template>
    <template #designation>
      <property-item column="steel_c" :name="$t('detail.column.steel_type')">
        {{ column.steel_c }}
      </property-item>
      <property-item column="f_yn" :name="$t('detail.column.nominal_yield_stress')" unit="MPa">
        {{ formatNumber(column, 'f_yn') }}
      </property-item>
      <property-item
        column="f_ymf"
        :name="$t('detail.column.nominal_yield_stress_flange')"
        unit="MPa"
      >
        {{ formatNumber(column, 'f_ymf') }}
      </property-item>
      <property-item column="f_ymw" :name="$t('detail.column.nominal_yield_stress_web')" unit="MPa">
        {{ formatNumber(column, 'f_ymw') }}
      </property-item>
    </template>
  </common-detail>
</template>
