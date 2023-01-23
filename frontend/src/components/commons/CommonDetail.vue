<script setup lang="ts">
import MultipleLineChart from "@/components/commons/charts/MultipleLineChart.vue";
import SimpleLineChart from "@/components/commons/charts/SimpleLineChart.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { primaryColor, secondaryColor } from "@/utils/vuetify";
import { withDefaults, defineProps, defineEmits } from "vue";
import { CarouselItem } from "@/utils/detail";

export interface Props {
  reference: string;
  link: string | undefined;
  carouselItems?: CarouselItem[][];
}
const props = withDefaults(defineProps<Props>(), {
  carouselItems: () => [],
});
const emit = defineEmits<{
  (e: "close"): void;
}>();

const chartHeight = 300;
const chartColor = primaryColor;
const chartColors = [primaryColor, secondaryColor];
</script>

<template>
  <v-card>
    <v-card-title>
      <slot name="title"></slot>
      <v-spacer></v-spacer>
      <v-btn color="primary" text @click="emit('close')">
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
        v-if="props.carouselItems.length > 0"
        :height="chartHeight"
        hide-delimiters
        :show-arrows="props.carouselItems.length > 1"
      >
        <v-carousel-item
          v-for="(carouselItem, carouselIndex) in props.carouselItems"
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

<style lang="scss" scoped>
.v-carousel__item > .v-responsive__content {
  display: flex;
  justify-content: center;
}
</style>
