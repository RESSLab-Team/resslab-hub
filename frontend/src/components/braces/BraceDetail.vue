<template>
  <common-detail
    :reference="reference"
    :link="link"
    :carousel-items="carouselItems"
    @close="close"
  >
    <template #title>
      {{ brace.investigator }} ({{ brace.date }}) -
      {{ brace.specimen_ID }}
    </template>
    <template #body>
      <v-row>
        <v-col cols="6">
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
              {{ brace.reinforcement_pl | formatString }}
            </property-item>
          </template>
        </v-col>
        <v-col cols="6">
          <h2>Steel Material Designation</h2>
          <h3>Brace</h3>
          <property-item name="Steel type">
            {{ brace.steel }}
          </property-item>
          <property-item name="Nominal yield stress" unit="MPa">
            {{ brace.f_yn | formatNumber }}
          </property-item>
          <property-item name="Measured yield stress" unit="MPa">
            {{ brace.fy_m | formatNumber }}
          </property-item>
          <property-item name="Ultimate tensile stress" unit="MPa">
            {{ brace.f_um | formatNumber }}
          </property-item>
          <h3>Gusset Plate</h3>
          <template v-if="isGussetPlate">
            <property-item name="Steel type">
              {{ brace.steel_gp }}
            </property-item>
            <property-item name="Nominal yield stress" unit="MPa">
              {{ brace.f_yn_gp | formatNumber }}
            </property-item>
            <property-item name="Measured yield stress" unit="MPa">
              {{ brace.f_ym_gp | formatNumber }}
            </property-item>
            <property-item name="Ultimate tensile stress" unit="MPa">
              {{ brace.f_um_gp | formatNumber }}
            </property-item>
          </template>
          <template v-else>
            The configuration does not include gusset plates
          </template>
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="12">
          <v-img :src="imageTypeSrc" />
        </v-col>
      </v-row>
    </template>
  </common-detail>
</template>

<script lang="ts">
import { BraceModel } from "@/backend";
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
export default class BraceDetail extends CommonDetailMixin {
  @VModel({ type: Object })
  readonly brace!: BraceModel;

  get reference(): string {
    return this.brace.reference;
  }

  get link(): string {
    return this.brace.link;
  }

  get carouselItems(): CarouselItem[][] {
    return [
      this.brace.displacement_count > 0
        ? [
            {
              promise: this.displacementMoment,
              title: "Force Displacement",
              xAxisName: "Displacement [mm]",
              yAxisName: "Force [kN]",
            },
          ]
        : [],
    ].filter((item) => item.length > 0);
  }

  get displacementMoment(): Promise<AxiosResponse<number[][]>> {
    return this.$bracesApi.getBracesDisplacement(this.brace.id);
  }

  get isGussetPlate(): boolean {
    return this.brace.boundary_condition === "Gusset plate";
  }

  get imageTypeSrc(): string | undefined {
    switch (this.brace.boundary_condition) {
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
  }
}
</script>
