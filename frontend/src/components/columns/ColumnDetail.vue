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
          <v-img contain max-height="256" :src="imageSrc"></v-img>
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

<script lang="ts">
import { ColumnModel } from "@/backend";
import CommonDetail from "@/components/commons/CommonDetail.vue";
import CommonDetailMixin from "@/components/commons/CommonDetailMixin.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { getColumnImage } from "@/utils/component";
import { CarouselItem } from "@/utils/detail";
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
      this.column.moment_strong_count > 0 || this.column.moment_weak_count > 0
        ? [
            {
              hidden: this.column.moment_strong_count === 0,
              promise: this.momentStrongPromise,
              title: "Moment Strong",
              xAxisName: "Chord Rotation [rads]",
              yAxisName: "Moment [kN-mm]",
            },
            {
              hidden: this.column.moment_weak_count === 0,
              promise: this.momentWeakPromise,
              title: "Moment Weak",
              xAxisName: "Chord Rotation [rads]",
              yAxisName: "Moment [kN-mm]",
            },
          ]
        : [],
    ].filter((item) => item.length > 0);
  }

  get momentStrongPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$columnsApi.getColumnsMomentStrong(this.column.id);
  }

  get momentWeakPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$columnsApi.getColumnsMomentWeak(this.column.id);
  }

  get axialShorteningPromise(): Promise<AxiosResponse<number[][]>> {
    return this.$columnsApi.getColumnsAxialShortening(this.column.id);
  }

  get imageSrc(): string | undefined {
    return getColumnImage(
      this.column.axis_of_bending,
      this.column.boundary_condition,
      this.column.direction_lp
    );
  }
}
</script>
