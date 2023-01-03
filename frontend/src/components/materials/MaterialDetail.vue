<template>
  <common-detail
    :reference="reference"
    :link="link"
    :carousel-items="carouselItems"
    @close="close"
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
              {{ material.fy_n__mpa_ | formatNumber }}
            </property-item>
            <property-item name="Measured yield stress" unit="MPa">
              {{ material.yield_stress__mpa_ | formatNumber }}
            </property-item>
            <property-item name="Nominal ultimate stress" unit="MPa">
              {{ material.fu_n__mpa_ | formatNumber }}
            </property-item>
          </p>
        </v-col>
        <v-col cols="6">
          <v-img contain :src="imageSrc"></v-img>
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>

<script lang="ts">
import { MaterialModel } from "@/backend";
import CommonDetail, {
  CarouselItem,
} from "@/components/commons/CommonDetail.vue";
import CommonDetailMixin from "@/components/commons/CommonDetailMixin.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { publicPath } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Component, VModel } from "vue-property-decorator";

@Component({
  components: {
    CommonDetail,
    PropertyItem,
  },
  filters: {
    formatNumber: function (value?: number) {
      return value ?? "Not Reported";
    },
    formatString: function (value: string | null): string {
      if (value === null) {
        return "No";
      } else if (value === "NR") {
        return "Not Reported";
      } else {
        return value;
      }
    },
  },
})
export default class MaterialDetail extends CommonDetailMixin {
  @VModel({ type: Object })
  readonly material!: MaterialModel;

  get reference(): string {
    return this.material.reference;
  }

  get link(): string {
    return this.material.link;
  }

  get carouselItems(): CarouselItem[][] {
    const items: CarouselItem[][] = [];
    if (this.material.stress_strain_count > 0) {
      items.push([
        {
          promise: this.stressStrain,
          title: "Stress Strain",
          xAxisName: "e",
          yAxisName: "σ [MPa]",
        },
      ]);
    }
    return items;
  }

  get stressStrain(): Promise<AxiosResponse<number[][]>> {
    return this.$materialsApi.getMaterialsStressStrain(this.material.id);
  }

  get imageSrc(): string {
    return publicPath + "img/material/detail.png";
  }
}
</script>
