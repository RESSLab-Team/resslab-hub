<template>
  <common-detail
    :reference="reference"
    :link="link"
    :carousel-items="carouselItems"
    @close="close"
  ></common-detail>
</template>

<style lang="scss">
.v-carousel__item > .v-responsive__content {
  display: flex;
  justify-content: center;
}
</style>

<script lang="ts">
import { ColumnModel } from "@/backend";
import CommonDetail, {
  CarouselItem,
} from "@/components/commons/CommonDetail.vue";
import CommonDetailMixin from "@/components/commons/CommonDetailMixin.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
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
    return this.column.experimental_program; //FIXME
  }

  get link(): string {
    return this.column.experimental_program; //FIXME
  }

  get carouselItems(): CarouselItem[][] {
    return []; //FIXME
  }
}
</script>
