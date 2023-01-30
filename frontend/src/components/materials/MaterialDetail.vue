<script setup lang="ts">
import { MaterialModel } from "@/backend";
import CommonDetail, {
  DetailCarouselItem,
} from "@/components/commons/CommonDetail.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { materialsApi } from "@/plugins/axios";
import { publicPath } from "@/utils/common";
import { computeUvcStress } from "@/utils/material";
import { zip } from "lodash";
import { defineProps, defineEmits, watch, ref } from "vue";
import { formatNumber } from "@/utils/formatter";
import { LineSeriesOption } from "echarts";

const props = defineProps<{
  material: MaterialModel;
}>();
const emit = defineEmits<{
  (e: "close"): void;
}>();

const carouselItems = ref<DetailCarouselItem[][]>([]);

watch(
  () => props.material,
  (material) => {
    carouselItems.value = [
      [
        {
          count: material.stress_strain_count,
          promise: materialsApi
            .getMaterialsStressStrain(material.id)
            .then((response) => response.data)
            .then((series) => {
              const stressStrain = series.map((serie) => [serie[1], serie[0]]);
              const strain = series.map((serie) => serie[1]);
              const uvcStress = computeUvcStress(
                strain,
                material.uvc_e__mpa_ * 1000,
                material.uvc_sigma__mpa_,
                material.uvc_q__mpa_,
                material.uvc_b,
                material.uvc_d__mpa_,
                material.uvc_a,
                [
                  {
                    c: material.uvc_c1__mpa_,
                    gamma: material.uvc_g1,
                  },
                  {
                    c: material.uvc_c2__mpa_,
                    gamma: material.uvc_g2,
                  },
                ]
              );
              const uvc = zip(strain, uvcStress).filter(
                (v): v is [number, number] =>
                  v[0] !== undefined && v[1] !== undefined
              );
              return [
                {
                  name: "Stress Strain",
                  data: stressStrain,
                },
                {
                  name: "uvc",
                  data: uvc,
                },
              ] as LineSeriesOption[];
            }),
          title: "Stress Strain with UVC",
          xAxisName: "ε",
          yAxisName: "σ [MPa]",
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
    :reference="material.reference"
    :link="material.link"
    :carousel-items="carouselItems"
    @close="emit('close')"
  >
    <template #title>
      {{ material.experimental_program }} ({{ material.date }}) -
      {{ material.id }}
    </template>
    <template #body>
      <v-row>
        <v-col cols="6">
          <h2>Structural Steel Element</h2>
          <p>
            <property-item name="Profile type">
              {{ material.profile_type }}
            </property-item>
            <property-item name="Cross section">
              {{ material.profile }} {{ material.source }}
            </property-item>
            <property-item name="Reference round coupon">
              {{ material.size }}
            </property-item>
            <property-item name="Temperature" unit="°C">
              {{ material.t_a__deg_c_ }}
            </property-item>
          </p>
          <h2>Steel Material Designation</h2>
          <p>
            <property-item name="Steel type">
              {{ material.grade }} {{ material.spec }}
            </property-item>
            <property-item name="Nominal yield stress" unit="MPa">
              {{ formatNumber(material.fy_n__mpa_) }}
            </property-item>
            <property-item name="Measured yield stress" unit="MPa">
              {{ formatNumber(material.yield_stress__mpa_) }}
            </property-item>
            <property-item name="Nominal ultimate stress" unit="MPa">
              {{ formatNumber(material.fu_n__mpa_) }}
            </property-item>
          </p>
        </v-col>
        <v-col cols="6">
          <v-img contain :src="publicPath + 'img/material/detail.png'" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
