<script setup lang="ts">
import type { BraceField, ColumnField, ConnectionField, MaterialField } from '@/backend'
import InfoTooltip from '@/components/commons/InfoTooltip.vue'
import OverviewMap from '@/components/commons/OverviewMap.vue'
import { analyticsApi, bracesApi, columnsApi, connectionsApi, materialsApi } from '@/plugins/axios'
import { publicPath } from '@/utils/common'
import { chain } from 'lodash'
import { onMounted, ref, shallowRef, triggerRef } from 'vue'

const carouselImages: {
  src: string
  credit: string
}[] = [
  'El Jisr and Lignos (2022)',
  'Elkady and Lignos (2018)',
  'Prof. Dimitrios Lignos, EPFL',
  'Andronikos Skiadopoulos, EPFL',
  'Suzuki and Lignos (2021)',
  'Skiadopoulos and Lignos (2022)',
  'Elkady and Lignos (2018)',
  'Andronikos Skiadopoulos, EPFL'
].map((credit, index) => ({
  src: publicPath + `img/home/Photo${index + 1}.jpg`,
  credit: credit
}))

const logos: {
  src: string
  url: string
}[] = [
  {
    src: publicPath + 'logo/resslab_logo_v1.svg',
    url: 'https://www.epfl.ch/labs/resslab'
  },
  {
    src: publicPath + 'logo/EPFL_Logo_184X53.svg',
    url: 'https://www.epfl.ch'
  },

  {
    src: publicPath + 'logo/logo_IT4R.svg',
    url: 'https://enac-it4r.epfl.ch'
  },
  {
    src: publicPath + 'logo/SNF_logo_standard_web_color_pos_e.svg',
    url: 'https://www.snf.ch'
  }
]

const imageIndex = ref(0)
const indicators = shallowRef<
  Record<'test' | 'university' | 'user', { text: string; count: number | string }>
>({
  test: {
    text: 'Tests',
    count: '~580'
  },
  university: {
    text: 'Universities contributed',
    count: '~30'
  },
  user: {
    text: 'Users worldwide',
    count: '~160'
  }
})

onMounted(() => {
  // Get test count
  Promise.all([
    bracesApi.getBracesDistinct(),
    columnsApi.getColumnsDistinct(),
    connectionsApi.getConnectionsDistinct(),
    materialsApi.getMaterialsDistinct()
  ])
    .then((responses) =>
      chain(responses)
        .flatMap((response) => response.data)
        .sum()
        .value()
    )
    .then((count) => {
      indicators.value.test.count = count
      triggerRef(indicators)
    })

  // Get university count
  const latLngFields: (BraceField & ColumnField & ConnectionField & MaterialField)[] = [
    'latitude',
    'longitude'
  ]
  Promise.all([
    bracesApi.getBracesCounts(latLngFields),
    columnsApi.getColumnsCounts(latLngFields),
    connectionsApi.getConnectionsCounts(latLngFields),
    materialsApi.getMaterialsCounts(latLngFields)
  ])
    .then((responses) =>
      chain(responses)
        .flatMap((response) => response.data)
        .uniqBy((count) => count.names)
        .size()
        .value()
    )
    .then((count) => {
      indicators.value.university.count = count
      triggerRef(indicators)
    })

  // Get user count
  analyticsApi
    .getUsers()
    .then((response) => response.data)
    .then((count) => {
      indicators.value.user.count = count
      triggerRef(indicators)
    })
})
</script>

<template>
  <v-container class="text-justify">
    <v-row>
      <v-col>
        <v-card>
          <v-responsive content-class="d-flex align-center" height="256px">
            <video autoplay loop muted preload="auto">
              <source :src="publicPath + 'video/steel-mrf-front-page.mp4'" type="video/mp4" />
            </video>
            <v-overlay
              class="align-center"
              contained
              :model-value="true"
              persistent
              no-click-animation
            >
              <h1 class="pa-5 text-center text-white">
                RESSLab Hub: Open-access databases and models for design and assessment of steel
                structures
              </h1>
            </v-overlay>
          </v-responsive>
        </v-card>
      </v-col>
    </v-row>
    <v-row class="">
      <v-col>
        <v-card class="fill-height">
          <div class="pa-5">
            <p>
              Recent developments in Performance-Based Earthquake Engineering enable studies to
              benchmark the seismic performance of infrastructure systems, further develop our codes
              and standards and to minimize the impacts of earthquakes worldwide. Moreover,
              digitalization of our cities requires the use of standardized predictive models for
              maintenance and life-cycle assessment of infrastructure systems. Within such a
              context, the RESSLab-hub provides open-access to the engineering and research
              communities to databases along with state-of-the-art modeling with the overarching
              goal to advance knowledge for minimizing the earthquake risk of steel and
              composite-steel concrete structures.
            </p>
            <br />
            <p>RESSLab Hub is composed of :</p>
            <p>
              - Databases
              <info-tooltip>
                A series of databases have been developed with enhanced visualization features for
                efficient search and data exploitation. The databases provide access to physical
                experiments of a rich set of structural steel materials, structural components and
                connections, residual stress measurements that were tested worldwide since the
                1970s. In particular, the databases include highly heterogenous data in a consistent
                format with parallel axis search and visualization capabilities. Fully digitized
                experimental data is made available that were extracted from experimental reports.
              </info-tooltip>
            </p>
            <p>
              - Component Models
              <info-tooltip>
                A web-based interactive module allows for the automatically constructed backbone and
                first-cycle envelope curves for structural steel components for direct use in
                nonlinear static and dynamic analyses procedures. This module incorporates the
                state-of-the-art in component modeling for seismic assessment of existing structures
                in North America and Europe. Besides the use of built-up cross sections, it links
                with currently available cross-sectional databases from North America, Europe and
                Japan to extract geometric features from standardized hot-rolled profiles, which are
                currently used in steel construction worldwide.
              </info-tooltip>
            </p>
            <p>
              - Fragility Curves
              <info-tooltip>
                A web-based interactive tool enables the exploitation of fragility curves for
                structural components that allows for financial loss estimation within the PBEE
                framework. The fragility curves are either univariate or multivariate depending on
                the component modeling resolution of interest. Visualization features include bar
                plots to enable exploitation of fragility curves and surfaces based on pertinent
                geometric and material parameters of interest.
              </info-tooltip>
            </p>
            <p>
              - ... and future updates
              <info-tooltip>
                Other databases and web-based interactive tools are currently under development.
                Stay tuned for future updates.
              </info-tooltip>
            </p>
          </div>
        </v-card>
      </v-col>
      <v-col lg="7" xl="8">
        <v-card class="fill-height">
          <overview-map />
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-card class="pa-5" color="secondary">
          <v-row>
            <v-col
              v-for="(item, index) in indicators"
              :key="index"
              class="d-flex flex-column align-center"
            >
              <h1>
                {{ item.count }}
              </h1>
              <span>{{ item.text }}</span>
            </v-col>
          </v-row>
        </v-card>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="7">
        <v-card class="fill-height pa-5">
          <span>Tutorial video will be available here</span>
        </v-card>
      </v-col>
      <v-col cols="5">
        <v-card class="rounded pa-5">
          <v-carousel
            v-model="imageIndex"
            class="bg-secondary rounded"
            cycle
            height="500"
            hide-delimiter-background
            :show-arrows="false"
          >
            <v-carousel-item v-for="(image, index) in carouselImages" :key="index" cover>
              <v-img :src="image.src" height="100%" />
            </v-carousel-item>
          </v-carousel>
          <v-card-text class="pa-0 pt-5 mb-0 text-right">
            Credits: {{ carouselImages[imageIndex].credit }}
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    <v-row class="my-10">
      <v-col v-for="(logo, index) in logos" :key="index">
        <a :href="logo.url" target="_blank">
          <v-img :src="logo.src" max-height="64" />
        </a>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-card class="rounded">
          <div class="pa-5">
            <h1>Copyrights</h1>
            <p>
              The databases in RESSLab-hub were assembled as a service to the research and practice
              communities in earthquake engineering. The assembled data, which have been fully
              digitized from various experimental reports, are shared under the
              <a href="https://creativecommons.org/licenses/by/2.0/legalcode" target="_blank"
                >Creative Commons Attribution 2.0 Generic</a
              >
              and the
              <a
                href="https://github.com/amaelkady/Steel-Columns-Test-Data/blob/main/LICENSE"
                target="_blank"
                >GNU General Public</a
              >
              licences. EPFL, and the researchers who performed the experiments make no warranties
              to the accuracy of the information that has been collected and provided in this
              website. If you have any questions, comments or suggestions, please contact
              <a href="https://people.epfl.ch/dimitrios.lignos" target="_blank"
                >Prof. Dimitrios Lignos</a
              >
              at <a href="https://www.epfl.ch" target="_blank">EPFL</a>.
            </p>
          </div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
