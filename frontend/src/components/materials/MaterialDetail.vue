<script setup lang="ts">
import { MaterialModel } from "@/backend";
import CommonDetail, {
  CarouselItem,
} from "@/components/commons/CommonDetail.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { materialsApi } from "@/plugins/axios";
import { publicPath } from "@/utils/common";
import { computeUvcStress } from "@/utils/material";
import { secondaryColor } from "@/utils/vuetify";
import { zip } from "lodash";
import { computed, defineProps, defineEmits, ref } from "vue";
import { formatNumber } from "@/utils/formatter";

const props = defineProps<{
  material: MaterialModel;
}>();
const emit = defineEmits<{
  (e: "close"): void;
}>();

const debugStrain = ref<number[]>([]);

const carouselItems = computed<CarouselItem[][]>(() => {
  const items: CarouselItem[][] = [];
  if (props.material.stress_strain_count > 0) {
    items.push([
      {
        promise: stressStrain.value,
        title: "Stress Strain",
        xAxisName: "ε",
        yAxisName: "σ [MPa]",
      },
      {
        promise: uvc.value,
        title: "Updated Voce-Chaboche",
        xAxisName: "ε",
        yAxisName: "σ [MPa]",
        color: secondaryColor,
      },
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
      debugStrain.value = strain;
      const uvcStress = computeUvcStress(
        strain,
        props.material.uvc_e__mpa_,
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
        <v-col>
          <v-expansion-panels>
            <v-expansion-panel>
              <v-expansion-panel-header>Parameters</v-expansion-panel-header>
              <v-expansion-panel-content>
                <property-item name="eTrue">
                  {{ debugStrain }}
                </property-item>
                <property-item name="E">
                  {{ material.uvc_e__mpa_ }}
                </property-item>
                <property-item name="sy_0">
                  {{ material.uvc_sigma__mpa_ }}
                </property-item>
                <property-item name="Q">
                  {{ material.uvc_q__mpa_ }}
                </property-item>
                <property-item name="b">
                  {{ material.uvc_b }}
                </property-item>
                <property-item name="D">
                  {{ material.uvc_d__mpa_ }}
                </property-item>
                <property-item name="a">
                  {{ material.uvc_a }}
                </property-item>
                <property-item name="a">
                  {{
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
                  }}
                </property-item>
              </v-expansion-panel-content>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-col>
      </v-row>
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
