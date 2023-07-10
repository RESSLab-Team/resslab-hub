<script setup lang="ts">
import UnitLineChart from '@/components/commons/charts/UnitLineChart.vue'
import PropertyItem from '@/components/commons/PropertyItem.vue'
import { mdiClose } from '@mdi/js'
import type { AxiosResponse } from 'axios'
import type { LineSeriesOption } from 'echarts'
import { ref, watch } from 'vue'

export interface DetailCarouselItem {
  count?: number
  noCount?: boolean
  promise?: Promise<AxiosResponse<number[][]> | LineSeriesOption[]>
  title: string
  axisPointerType?: string
  xAxisName: string
  yAxisName: string
}

export interface Props {
  reference: string
  link: string | undefined
  carouselItems?: DetailCarouselItem[][]
  carouselHeight?: number
  aspectRatio?: number
}
const props = withDefaults(defineProps<Props>(), {
  carouselItems: () => [],
  carouselHeight: 300,
  aspectRatio: 1.5
})
const emit = defineEmits<{
  (e: 'close'): void
}>()

type SeriesCarouselItem = Omit<DetailCarouselItem, 'promise'> & {
  series: LineSeriesOption[]
}

const seriesCarouselItems = ref<SeriesCarouselItem[][]>([])

watch(
  () => props.carouselItems,
  async (carouselItems) => {
    seriesCarouselItems.value = (
      await Promise.all(
        carouselItems.map((carouselItem) =>
          Promise.all(
            carouselItem
              .filter((item) => item.noCount || (item.count && item.count > 0))
              .map(async (item) => {
                const response = await item.promise
                const series: LineSeriesOption[] = Array.isArray(response)
                  ? response
                  : [{ data: response?.data }]
                const carouselItem: SeriesCarouselItem = {
                  series: series,
                  ...item
                }
                return carouselItem
              })
          )
        )
      )
    ).filter((row) => row.length > 0)
  },
  {
    immediate: true
  }
)
</script>

<template>
  <v-card>
    <v-card-title class="d-flex">
      <slot name="title" />
      <v-spacer />
      <v-btn color="primary" :prepend-icon="mdiClose" variant="text" @click="emit('close')">
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
            <template v-for="(item, index) in carouselItem" :key="index">
              <v-col class="d-flex justify-center" :cols="12 / carouselItem.length">
                <unit-line-chart
                  :aspect-ratio="aspectRatio"
                  :max-width="carouselHeight * aspectRatio"
                  v-bind="item"
                />
              </v-col>
            </template>
          </v-row>
        </v-carousel-item>
      </v-carousel>
      <slot v-if="$slots.body" name="body" />
      <template v-else>
        <h2>Loading and Geometric Parameters</h2>
        <slot name="parameters" />
        <h2>Steel Material Designation</h2>
        <slot name="designation" />
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
