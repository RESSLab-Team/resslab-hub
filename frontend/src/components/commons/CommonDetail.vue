<script setup lang="ts">
import EyebrowText from '@/components/commons/EyebrowText.vue'
import UnitLineChart from '@/components/commons/charts/UnitLineChart.vue'
import { safeHref } from '@/utils/common'
import { mdiClose, mdiOpenInNew } from '@mdi/js'
import type { AxiosResponse } from 'axios'
import type { LineSeriesOption } from 'echarts'
import { computed, ref, watch } from 'vue'

export interface DetailCarouselItem {
  count?: number
  noCount?: boolean
  series?: LineSeriesOption[]
  promise?: Promise<AxiosResponse<number[][]> | LineSeriesOption[]>
  title: string
  axisPointerType?: string
  xAxisName: string
  yAxisName: string
  xAxisMin?: number
  yAxisMin?: number
  xAxisMax?: number
  yAxisMax?: number
}

export interface Props {
  reference: string
  link: string | null | undefined
  /** Uppercase kicker above the title, e.g. "RBS · Connection". */
  eyebrow?: string
  /** Monospace specimen identifier shown under the title. */
  specimenId?: string
  carouselItems?: DetailCarouselItem[][]
  carouselHeight?: number
  aspectRatio?: number
}
const props = withDefaults(defineProps<Props>(), {
  eyebrow: undefined,
  specimenId: undefined,
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
const page = ref<number>(0)

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
    page.value = 0
  },
  {
    immediate: true
  }
)

const currentPage = computed<SeriesCarouselItem[]>(
  () => seriesCarouselItems.value[page.value] ?? []
)
const pageTitle = computed<string>(() => currentPage.value.map((item) => item.title).join(' · '))

function previousPage(): void {
  const total = seriesCarouselItems.value.length
  page.value = (page.value - 1 + total) % total
}
function nextPage(): void {
  const total = seriesCarouselItems.value.length
  page.value = (page.value + 1) % total
}
</script>

<template>
  <div class="detail-panel">
    <div class="drawer-head">
      <div class="cd-title-block">
        <div v-if="eyebrow" class="cd-eyebrow"><eyebrow-text :text="eyebrow" /></div>
        <h2 class="cd-title"><slot name="title" /></h2>
        <div v-if="specimenId" class="cd-title-id">{{ specimenId }}</div>
      </div>
      <div class="cd-head-actions">
        <slot name="actions" />
        <button class="hdr-icon-btn" :aria-label="$t('commons.close')" @click="emit('close')">
          <v-icon :icon="mdiClose" size="16" />
        </button>
      </div>
    </div>

    <div class="drawer-body">
      <div class="cd-publication">
        <div class="cd-publication-label">{{ $t('commons.publication') }}</div>
        <a v-if="link" class="cd-publication-ref" :href="safeHref(link)" target="_blank" rel="noreferrer">
          {{ reference }}
          <v-icon :icon="mdiOpenInNew" size="11" />
        </a>
        <span v-else class="cd-publication-ref">{{ reference }}</span>
      </div>

      <div v-if="seriesCarouselItems.length > 0" class="cd-carousel">
        <div class="cd-carousel-head">
          <div class="cd-carousel-title">{{ pageTitle }}</div>
          <div v-if="seriesCarouselItems.length > 1" class="cd-carousel-nav">
            <button
              class="cd-carousel-btn"
              :aria-label="$t('commons.previous')"
              @click="previousPage"
            >
              ‹
            </button>
            <span class="cd-carousel-counter">
              {{ page + 1 }} / {{ seriesCarouselItems.length }}
            </span>
            <button class="cd-carousel-btn" :aria-label="$t('commons.next')" @click="nextPage">
              ›
            </button>
          </div>
        </div>
        <div class="cd-carousel-body">
          <div v-for="(item, index) in currentPage" :key="`${page}-${index}`" class="cd-chart-wrap">
            <div v-if="currentPage.length > 1" class="cd-chart-label">{{ item.title }}</div>
            <unit-line-chart
              :aspect-ratio="aspectRatio"
              :max-width="carouselHeight * aspectRatio"
              v-bind="item"
              title=""
            />
          </div>
        </div>
      </div>

      <slot v-if="$slots.body" name="body" />
      <template v-else>
        <h3 class="cd-section-h">{{ $t('commons.loading_geometric_parameters') }}</h3>
        <slot name="parameters" />
        <h3 class="cd-section-h">{{ $t('commons.steel_material_designation') }}</h3>
        <slot name="designation" />
      </template>
    </div>
  </div>
</template>
