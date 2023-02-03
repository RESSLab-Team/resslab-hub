<script setup lang="ts">
import { ColumnModel } from "@/backend";
import CommonDetail, {
  DetailCarouselItem,
} from "@/components/commons/CommonDetail.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { columnsApi } from "@/plugins/axios";
import { getColumnImage } from "@/utils/component";
import { defineProps, defineEmits, ref, watch, computed } from "vue";

const props = defineProps<{
  column: ColumnModel;
}>();
const emit = defineEmits<{
  (e: "close"): void;
}>();

const carouselItems = ref<DetailCarouselItem[][]>([]);

const imageSrc = computed<string | undefined>(() =>
  getColumnImage(
    props.column.axis_of_bending,
    props.column.boundary_condition,
    props.column.direction_lp
  )
);

watch(
  () => props.column,
  (column) => {
    carouselItems.value = [
      [
        {
          count: column.axial_shortening_count,
          promise: columnsApi.getColumnsAxialShortening(column.id),
          title: "Axial Shortening",
          xAxisName: "Chord Rotation [rads]",
          yAxisName: "Axial Shortening [mm]",
        },
      ],
      [
        {
          count: column.moment_strong_count,
          promise: columnsApi.getColumnsMomentStrong(column.id),
          title: "Moment Strong",
          xAxisName: "Chord Rotation [rads]",
          yAxisName: "Moment [kN-mm]",
        },
        {
          count: column.moment_weak_count,
          promise: columnsApi.getColumnsMomentWeak(column.id),
          title: "Moment Weak",
          xAxisName: "Chord Rotation [rads]",
          yAxisName: "Moment [kN-mm]",
        },
      ],
    ];
  },
  {
    immediate: true,
  }
);
</script>

<template>
  <common-detail
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
        <v-col cols="6">
          <property-item name="Loading protocol">
            {{ column.lateral_lp }}
          </property-item>
          <property-item name="Axial load ratio">
            {{ column.axial_lp }} (Pg/Py = {{ column.p_g_over_p_ym }})
          </property-item>
          <property-item name="Axis of bending">
            {{ column.axis_of_bending }}
          </property-item>
          <property-item name="Boundary conditions">
            {{ column.boundary_condition }}
          </property-item>
          <property-item name="Column cross section">
            {{ column.section_c }}
          </property-item>
          <property-item name="Member slenderness ratio, Lb/ry">
            {{ column.l_b_over_r_yc }}
          </property-item>
        </v-col>
        <v-col cols="6">
          <v-img contain max-height="256" :src="imageSrc" />
        </v-col>
      </v-row>
    </template>
    <template #designation>
      <property-item name="Steel type">
        {{ column.steel_c }}
      </property-item>
      <property-item name="Nominal yield stress" unit="MPa">
        {{ column.f_yn }}
      </property-item>
      <property-item name="Nominal yield stress (flange)" unit="MPa">
        {{ column.f_ymf }}
      </property-item>
      <property-item name="Nominal yield stress (web)" unit="MPa">
        {{ column.f_ymw }}
      </property-item>
    </template>
  </common-detail>
</template>
