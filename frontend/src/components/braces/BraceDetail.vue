<template>
  <common-detail
    :reference="reference"
    :link="link"
    :carousel-items="carouselItems"
    @close="close"
  >
  </common-detail>
</template>

<script lang="ts">
import { BraceModel } from "@/backend";
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
}
</script>
