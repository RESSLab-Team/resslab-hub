<script setup lang="ts">
import { EccentricBracedFrameField, type EccentricBracedFrameModel } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import SteelTypeCardTitle from '@/components/commons/SteelTypeCardTitle.vue'
import ResetChartButton from '@/components/commons/ResetChartButton.vue'

import EbfTable from '@/components/ebf/EbfTable.vue'
import EbfDetail from '@/components/ebf/EbfDetail.vue'
import EbfParallelChart from '@/components/ebf/charts/EbfParallelChart.vue'
import EbfDoubleChart from '@/components/ebf/charts/EbfDoubleChart.vue'
import EbfSingleChart from '@/components/ebf/charts/EbfSingleChart.vue'

import type { DoubleFields, ParallelField } from '@/composables/chart'
import { useDashboard } from '@/composables/dashboard'
import { useRoute, useRouter } from 'vue-router'
import colors from 'vuetify/lib/util/colors'

import { sectionTypeMapping } from '@/utils/ebf'
const route = useRoute()
const router = useRouter()
const { clickTableRow, closeDetail, item, query, search, searches, changeSearches, updatePage } =
  useDashboard<EccentricBracedFrameModel>(route, router, EccentricBracedFrameField)

const parallelFields: ParallelField<EccentricBracedFrameField>[] = [
  { id: EccentricBracedFrameField.E, name: 'e [mm]' },
  { id: EccentricBracedFrameField.LinkLoc, name: 'Location' },
  { id: EccentricBracedFrameField.SecType, name: 'Type' },
  { id: EccentricBracedFrameField.SgFlgLink, name: 'Material' },
  { id: EccentricBracedFrameField.OvAisc, name: 'Ω' },
  {
    id: EccentricBracedFrameField.ClassAisc,
    name: 'Link Classification',
    sortValues: ['long', 'intermediate', 'short']
  }
]

const yearSectionFields: DoubleFields<EccentricBracedFrameField> = [
  EccentricBracedFrameField.Year,
  {
    id: EccentricBracedFrameField.SecType,
    mapping: sectionTypeMapping
  }
]

const yearLinkFields: DoubleFields<EccentricBracedFrameField> = [
  EccentricBracedFrameField.Year,
  {
    id: EccentricBracedFrameField.ClassAisc,
    mapping: sectionTypeMapping
  }
]

const loadingProtocolField = EccentricBracedFrameField.LPTyp
const testSetupField = EccentricBracedFrameField.LConfi
const steelField = EccentricBracedFrameField.SgFlgLink
</script>

<template>
  <v-row>
    <v-col md="6">
      <v-row>
        <v-col cols="12">
          <ebf-table
            v-model:search="search"
            v-model:searches="searches"
            :query="query"
            @click:row="clickTableRow"
            @update:page="updatePage"
          />
        </v-col>
      </v-row>
      <v-row v-if="!item">
        <v-col cols="12">
          <ebf-parallel-chart
            :color="colors.orange"
            :fields="parallelFields"
            :query="query"
            @change:searches="changeSearches"
          />
        </v-col>
      </v-row>
    </v-col>
    <v-col md="6">
      <v-row v-if="item">
        <v-col cols="12">
          <ebf-detail :eccentric-braced-frame="item" @close="closeDetail" />
        </v-col>
      </v-row>
      <v-row v-else>
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title class="d-flex justify-space-between">
              Section Type
              <reset-chart-button
                :field="yearSectionFields"
                :is-filtered="yearSectionFields.some(field => query.includes(field as string))"
                @change:searches="changeSearches"
              />
            </v-card-title>
            <v-card-text>
              <ebf-double-chart
                :fields="yearSectionFields"
                :query="query"
                type="line"
                @change:searches="changeSearches"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card>
            <v-card-title class="d-flex justify-space-between">
              Link Type
              <reset-chart-button
                :field="yearLinkFields"
                :is-filtered="yearLinkFields.some(field => query.includes(field as string))"
                @change:searches="changeSearches"
              />
            </v-card-title>
            <v-card-text>
              <ebf-double-chart
                :fields="yearLinkFields"
                :query="query"
                :color="colors.purple"
                type="line"
                @change:searches="changeSearches"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col>
          <ebf-single-chart
            :show-reset="true"
            :color="colors.red"
            :field="loadingProtocolField"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <div>
                Loading Protocol
                <info-tooltip>
                  <p>This chart shows the different loading protocols used in EBF tests.</p>
                </info-tooltip>
              </div>
            </template>
          </ebf-single-chart>
        </v-col>
        <v-col cols="12">
          <ebf-single-chart
            :show-reset="true"
            :color="colors.blue"
            :field="testSetupField"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <div>
                Test Setup
                <info-tooltip>
                  <p>This chart shows the different test configurations:</p>
                  <ul>
                    <li>TF1 = Isolated link</li>
                    <li>TF2 = Link in bare frame</li>
                    <li>TF2C = Link in composite frame</li>
                    <li>TF3 = Link in system</li>
                  </ul>
                </info-tooltip>
              </div>
            </template>
          </ebf-single-chart>
        </v-col>
        <v-col>
          <ebf-single-chart
            :show-reset="true"
            :color="colors.deepPurple"
            :field="steelField"
            :query="query"
            @change:searches="changeSearches"
          >
            <template #title>
              <steel-type-card-title />
            </template>
          </ebf-single-chart>
        </v-col>
      </v-row>
    </v-col>
  </v-row>
</template>
