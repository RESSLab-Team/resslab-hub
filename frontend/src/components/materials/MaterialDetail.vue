<script setup lang="ts">
import { MaterialModel } from "@/backend";
import CommonDetail from "@/components/commons/CommonDetail.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { materialsApi } from "@/plugins/axios";
import { publicPath } from "@/utils/common";
import { computeUvcStress } from "@/utils/material";
import { zip } from "lodash";
import { computed, defineProps, defineEmits } from "vue";
import { formatNumber } from "@/utils/formatter";
import { CarouselItem } from "@/utils/detail";

const props = defineProps<{
  material: MaterialModel;
}>();
const emit = defineEmits<{
  (e: "close"): void;
}>();

const carouselItems = computed<CarouselItem[][]>(() => {
  const items: CarouselItem[][] = [];
  if (props.material.stress_strain_count > 0) {
    items.push([
      {
        promises: [stressStrain.value, uvc.value],
        title: "Stress Strain with UVC",
        xAxisName: "ε",
        yAxisName: "σ [MPa]",
      },
    ]);
  }
  return items;
});

const stressStrain = computed<Promise<number[][]>>(() => {
  // eslint-disable-next-line vue/no-async-in-computed-properties
  return materialsApi
    .getMaterialsStressStrain(props.material.id)
    .then((response) => response.data)
    .then((series) => series.map((serie) => [serie[1], serie[0]]));
});

const uvc = computed<Promise<number[][]>>(() => {
  // eslint-disable-next-line vue/no-async-in-computed-properties
  return materialsApi
    .getMaterialsStressStrain(props.material.id)
    .then((response) => response.data)
    .then((series) => {
      const strain = series.map((serie) => serie[1]);
      const uvcStress = computeUvcStress(
        strain,
        props.material.uvc_e__mpa_ * 1000,
        props.material.uvc_sigma__mpa_,
        props.material.uvc_q__mpa_,
        props.material.uvc_b,
        props.material.uvc_d__mpa_,
        props.material.uvc_a,
        [
          {
            c: props.material.uvc_c1__mpa_,
            gamma: props.material.uvc_g1,
          },
          {
            c: props.material.uvc_c2__mpa_,
            gamma: props.material.uvc_g2,
          },
        ]
      );
      return zip(strain, uvcStress).filter(
        (v): v is [number, number] => v[0] !== undefined && v[1] !== undefined
      );
    });
});
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
