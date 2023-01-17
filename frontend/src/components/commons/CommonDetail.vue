<template>
  <v-card>
    <v-card-title>
      <slot name="title"></slot>
      <v-spacer></v-spacer>
      <v-btn color="primary" text @click="close">
        <v-icon>mdi-close</v-icon>
        Close
      </v-btn>
    </v-card-title>
    <v-card-text>
      <p>
        <property-item name="Publication">
          <a v-if="link" :href="link" target="_blank">
            {{ reference }}
          </a>
          <span v-else>{{ reference }}</span>
        </property-item>
      </p>
      <v-carousel
        v-if="carouselItems.length > 0"
        :height="chartHeight"
        hide-delimiters
        :show-arrows="carouselItems.length > 1"
      >
        <v-carousel-item
          v-for="(carouselItem, carouselIndex) in carouselItems"
          :key="carouselIndex"
        >
          <v-row>
            <template v-for="(item, index) in carouselItem">
              <v-col
                v-if="!item.hidden"
                :key="index"
                class="d-flex justify-center"
                :cols="12 / carouselItem.filter((item) => !item.hidden).length"
              >
                <simple-line-chart
                  v-if="item.promise"
                  :color="item.color ?? chartColor"
                  :max-width="chartHeight"
                  :promise="item.promise"
                  :title="item.title"
                  :x-axis-name="item.xAxisName"
                  :y-axis-name="item.yAxisName"
                ></simple-line-chart>
                <multiple-line-chart
                  v-if="item.promises"
                  :colors="chartColors"
                  :max-width="chartHeight"
                  :promises="item.promises"
                  :title="item.title"
                  :x-axis-name="item.xAxisName"
                  :y-axis-name="item.yAxisName"
                ></multiple-line-chart>
              </v-col>
            </template>
          </v-row>
        </v-carousel-item>
      </v-carousel>
      <slot v-if="$slots.body" name="body"></slot>
      <template v-else>
        <h2>Loading and Geometric Parameters</h2>
        <slot name="parameters"></slot>
        <h2>Steel Material Designation</h2>
        <slot name="designation"></slot>
      </template>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import MultipleLineChart, {
  Response,
} from "@/components/commons/charts/MultipleLineChart.vue";
import SimpleLineChart from "@/components/commons/charts/SimpleLineChart.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { primaryColor, secondaryColor } from "@/utils/vuetify";
import { Component, Prop, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component({
  components: {
    MultipleLineChart,
    SimpleLineChart,
    PropertyItem,
  },
})
export default class CommonDetail extends Vue {
  readonly chartHeight = 300;
  readonly chartColor = primaryColor;
  readonly chartColors = [primaryColor, secondaryColor];

  @Prop(String)
  readonly reference!: string;
  @Prop(String)
  readonly link?: string;
  @Prop({ type: Array as () => CarouselItem[][], default: () => [] })
  readonly carouselItems!: CarouselItem[][];

  close(): void {
    this.$emit("close");
  }
}

export interface CarouselItem {
  hidden?: boolean;
  promise?: Promise<Response>;
  promises?: Promise<Response>[];
  title: string;
  xAxisName: string;
  yAxisName: string;
  color?: Color;
}
</script>

<style lang="scss">
.v-carousel__item > .v-responsive__content {
  display: flex;
  justify-content: center;
}
</style>
