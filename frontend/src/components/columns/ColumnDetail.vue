<template>
  <common-detail
    :reference="reference"
    :link="link"
    :carousel-items="carouselItems"
    @close="close"
  >
    <template #title>
      {{ column.experimental_program }} - ({{ column.date }}) -
      {{ column.specimen_designation }}
    </template>
    <template #parameters>
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

<script lang="ts">
import { ColumnModel } from "@/backend";
import CommonDetail, {
  CarouselItem,
} from "@/components/commons/CommonDetail.vue";
import CommonDetailMixin from "@/components/commons/CommonDetailMixin.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { AxiosResponse } from "axios";
import { Component, VModel } from "vue-property-decorator";

@Component({
  components: {
    CommonDetail,
    PropertyItem,
  },
})
export default class ColumnDetail extends CommonDetailMixin {
  @VModel({ type: Object })
  readonly column!: ColumnModel;

  get reference(): string {
    return this.column.reference;
  }

  get link(): string {
    return this.column.link;
  }

  get carouselItems(): CarouselItem[][] {
    return [
      this.column.moment_count > 0
        ? [
            {
              promise: this.momentPromise,
              title: "Moment",
              xAxisName: "Chord Rotation [rads]",
              yAxisName: "Moment [kN-mm]",
            },
          ]
        : [],
      this.column.axial_shortening_count > 0
        ? [
            {
              promise: this.axialShorteningPromise,
              title: "Axial Shortening",
              xAxisName: "Chord Rotation [rads]",
              yAxisName: "Axial Shortening [mm]",
            },
          ]
        : [],
    ].filter((item) => item.length > 0);
  }

  get momentPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$columnsApi.getColumnsMoment(this.column.id);
  }

  get axialShorteningPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$columnsApi.getColumnsAxialShortening(this.column.id);
  }
}
</script>
