<script setup lang="ts">
import { BraceModel } from "@/backend";
import CommonDetail, {
  DetailCarouselItem,
} from "@/components/commons/CommonDetail.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { bracesApi } from "@/plugins/axios";
import { publicPath } from "@/utils/common";
import { defineProps, defineEmits, ref, watch, computed } from "vue";

const props = defineProps<{
  brace: BraceModel;
}>();
const emit = defineEmits<{
  (e: "close"): void;
}>();

const carouselItems = ref<DetailCarouselItem[][]>([]);

const isGussetPlate = computed<boolean>(
  () => props.brace.boundary_condition === "Gusset plate"
);

const imageTypeSrc = computed<string | undefined>(() => {
  switch (props.brace.boundary_condition) {
    case "Gusset plate":
      return publicPath + "img/brace/type/gusset-plate.png";
    case "Pin-Pin end":
      return publicPath + "img/brace/type/pinned-end.png";
    case "Fixed-fixed end":
      return publicPath + "img/brace/type/fixed-end.png";
    case "Fixed_pinned end":
      return publicPath + "img/brace/type/fixed-pinned.png";
  }
  return undefined;
});

watch(
  () => props.brace,
  (brace) => {
    carouselItems.value = [
      [
        {
          count: brace.displacement_count,
          promise: bracesApi.getBracesDisplacement(brace.id),
          title: "Force Displacement",
          xAxisName: "Displacement [mm]",
          yAxisName: "Force [kN]",
        },
      ],
    ];
  },
  {
    immediate: true,
  }
);

function formatNumber(value?: number) {
  return value ?? "Not Reported";
}
function formatString(value?: string): string {
  if (value === undefined) {
    return "No";
  } else if (value === "NR") {
    return "Not Reported";
  } else {
    return value;
  }
}
</script>

<template>
  <common-detail
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
              <h2>Loading and Geometric Parameters</h2>
              <property-item name="Loading protocol">
                {{ brace.loading_protocol }}
              </property-item>
              <property-item name="Brace boundary conditions">
                {{ brace.boundary_condition }}
              </property-item>
              <property-item name="Brace cross section shape">
                {{ brace.cross_section_shape }}
              </property-item>
              <property-item name="Brace cross section size">
                {{ brace.cross_section_size }}
              </property-item>
              <property-item name="Member slenderness ratio KL/r">
                {{ brace.kl_r }}
              </property-item>
              <template v-if="isGussetPlate">
                <property-item name="Gusset plate thickness" unit="mm">
                  {{ brace.t_t }}
                </property-item>
                <property-item name="Reinforcement plate">
                  {{ formatString(brace.reinforcement_pl) }}
                </property-item>
              </template>
            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <h2>Steel Material Designation</h2>
              <h3>Brace</h3>
              <property-item name="Steel type">
                {{ brace.steel }}
              </property-item>
              <property-item name="Nominal yield stress" unit="MPa">
                {{ formatNumber(brace.f_yn) }}
              </property-item>
              <property-item name="Measured yield stress" unit="MPa">
                {{ formatNumber(brace.fy_m) }}
              </property-item>
              <property-item name="Ultimate tensile stress" unit="MPa">
                {{ formatNumber(brace.f_um) }}
              </property-item>
              <h3>Gusset Plate</h3>
              <template v-if="isGussetPlate">
                <property-item name="Steel type">
                  {{ brace.steel_gp }}
                </property-item>
                <property-item name="Nominal yield stress" unit="MPa">
                  {{ formatNumber(brace.f_yn_gp) }}
                </property-item>
                <property-item name="Measured yield stress" unit="MPa">
                  {{ formatNumber(brace.f_ym_gp) }}
                </property-item>
                <property-item name="Ultimate tensile stress" unit="MPa">
                  {{ formatNumber(brace.f_um_gp) }}
                </property-item>
              </template>
              <template v-else>
                The configuration does not include gusset plates
              </template>
            </v-col>
          </v-row>
        </v-col>
        <v-col cols="6">
          <v-img contain :src="imageTypeSrc" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>
