<script setup lang="ts">
import MultipleLineChart from "@/components/commons/charts/MultipleLineChart.vue";
import PropertyItem from "@/components/commons/PropertyItem.vue";
import { primaryColor, secondaryColor } from "@/utils/vuetify";
import { withDefaults, defineProps, defineEmits, ref, watch } from "vue";
import { LineSeriesOption } from "echarts";
import { AxiosResponse } from "axios";

export interface DetailCarouselItem {
  count: number;
  promise?: Promise<AxiosResponse<number[][]> | LineSeriesOption[]>;
  title: string;
  xAxisName: string;
  yAxisName: string;
}

export interface Props {
  reference: string;
  link: string | undefined;
  carouselItems?: DetailCarouselItem[][];
}
const props = withDefaults(defineProps<Props>(), {
  carouselItems: () => [],
});
const emit = defineEmits<{
  (e: "close"): void;
}>();

const carouselHeight = 300;

type SeriesCarouselItem = Omit<DetailCarouselItem, "promise"> & {
  series: LineSeriesOption[];
};

const seriesCarouselItems = ref<SeriesCarouselItem[][]>([]);

watch(
  () => props.carouselItems,
  async (carouselItems) => {
    seriesCarouselItems.value = (
      await Promise.all(
        carouselItems.map((carouselItem) =>
          Promise.all(
            carouselItem
              .filter((item) => item.count > 0)
              .map(async (item) => {
                const response = await item.promise;
                const series: LineSeriesOption[] = Array.isArray(response)
                  ? response
                  : [{ data: response?.data }];
                const carouselItem: SeriesCarouselItem = {
                  series: series,
                  ...item,
                };
                return carouselItem;
              })
          )
        )
      )
    ).filter((row) => row.length > 0);
  },
  {
    immediate: true,
  }
);
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
        v-if="seriesCarouselItems.length > 0"
        :height="carouselHeight"
        hide-delimiters
        :show-arrows="seriesCarouselItems.length > 1"
      >
        <v-carousel-item
          v-for="(carouselItem, carouselIndex) in seriesCarouselItems"
          :key="carouselIndex"
        >
          <v-row>
            <template v-for="(item, index) in carouselItem">
              <v-col
                :key="index"
                class="d-flex justify-center"
                :cols="12 / carouselItem.length"
              >
                <multiple-line-chart
                  :colors="[primaryColor, secondaryColor]"
                  :max-width="carouselHeight"
                  v-bind="item"
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
