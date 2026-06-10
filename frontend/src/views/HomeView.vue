<script setup lang="ts">
import type {
  BraceField,
  ColumnField,
  ConnectionField,
  HSSColumnField,
  MaterialField
} from '@/backend'
import AppFooter from '@/components/layout/AppFooter.vue'
import OverviewMap from '@/components/map/OverviewMap.vue'
import {
  analyticsApi,
  bracesApi,
  columnsApi,
  connectionsApi,
  hssApi,
  materialsApi,
  residualsApi
} from '@/plugins/axios'
import { useCountsStore } from '@/stores/counts'
import { publicPath } from '@/utils/common'
import { DATABASES, TOOLS } from '@/utils/navigation'
import { mdiArrowRight } from '@mdi/js'
import { chain } from 'lodash'
import { computed, onMounted, ref } from 'vue'

const countsStore = useCountsStore()
const universityCount = ref<number | string>('…')
const userCount = ref<number | string>('…')

const keyNumbers = computed(() => [
  {
    num: countsStore.total != null ? countsStore.total.toLocaleString('en-CH') : '…',
    label: 'Experimental tests digitized'
  },
  { num: universityCount.value, label: 'Universities contributed' },
  { num: userCount.value, label: 'Researchers & engineers worldwide' },
  { num: DATABASES.length, label: 'Curated databases, one consistent format' }
])

onMounted(() => {
  countsStore.fetch()

  // Get university count
  const latLngFields: (BraceField &
    ColumnField &
    ConnectionField &
    MaterialField &
    HSSColumnField)[] = ['latitude', 'longitude']
  Promise.all([
    bracesApi.getBracesCounts(latLngFields),
    columnsApi.getColumnsCounts(latLngFields),
    connectionsApi.getConnectionsCounts(latLngFields),
    materialsApi.getMaterialsCounts(latLngFields),
    residualsApi.getResidualStressesCounts(latLngFields),
    hssApi.getHssColumnsCounts(latLngFields)
  ])
    .then((responses) =>
      chain(responses)
        .flatMap((response) => response.data)
        .uniqBy((count) => count.names)
        .size()
        .value()
    )
    .then((count) => {
      universityCount.value = count
    })

  // Get user count
  analyticsApi
    .getUsers()
    .then((response) => response.data)
    .then((count) => {
      userCount.value = count
    })
})
</script>

<template>
  <div>
    <!-- Hero — overlapping white text panel breaking the media edge -->
    <section class="hero">
      <div class="hero-text">
        <div class="hero-eyebrow">EPFL · RESSLab</div>
        <h1 class="hero-title">Open data for <em>seismic-resilient</em><br />steel structures.</h1>
        <p class="hero-lede">
          Curated experimental databases and state-of-the-art component models for performance-based
          earthquake engineering — assembled worldwide since the 1970s, fully digitized, freely
          accessible.
        </p>
        <div class="hero-cta">
          <router-link class="btn btn-primary" to="/connections/database">
            Browse databases
            <v-icon :icon="mdiArrowRight" size="14" />
          </router-link>
          <router-link class="btn btn-secondary" to="/about">About the project</router-link>
        </div>
      </div>
      <div class="hero-img">
        <video autoplay loop muted playsinline preload="auto">
          <source :src="publicPath + 'video/steel-mrf-front-page.mp4'" type="video/mp4" />
        </video>
        <div class="hero-img-credit">RESSLab, EPFL</div>
      </div>
    </section>

    <!-- Key numbers -->
    <div class="keynums">
      <div v-for="(item, index) in keyNumbers" :key="index" class="keynum">
        <div class="keynum-num">{{ item.num }}</div>
        <div class="keynum-bar" />
        <div class="keynum-label">{{ item.label }}</div>
      </div>
    </div>

    <!-- Databases -->
    <section class="section">
      <div class="section-head">
        <div>
          <div class="section-eyebrow">Databases</div>
          <h2 class="section-title">Nine curated datasets, one consistent format.</h2>
          <p class="section-sub">
            Digitized experimental data from labs worldwide. Filter by geometry, material and
            loading protocol; export reproducibly; cite original sources.
          </p>
        </div>
        <router-link class="section-link" to="/connections/database">
          View all databases →
        </router-link>
      </div>
      <div class="cat-grid">
        <router-link v-for="db in DATABASES" :key="db.id" class="cat-tile" :to="db.to">
          <div class="cat-tile-icon"><v-icon :icon="db.icon" size="22" /></div>
          <h3 class="cat-tile-title">{{ db.name }}</h3>
          <p class="cat-tile-desc">{{ db.desc }}</p>
          <div class="cat-tile-meta">
            <template v-if="countsStore.counts[db.id] != null">
              <strong>{{ countsStore.counts[db.id] }}</strong>
              <span>tests</span>
            </template>
            <span style="flex: 1" />
            <span class="cat-tab">{{ db.group }}</span>
          </div>
          <v-icon :icon="mdiArrowRight" size="16" class="cat-arrow" />
        </router-link>
      </div>
    </section>

    <!-- Worldwide reach + tutorial -->
    <section class="section section-bg-subtle">
      <div class="section-head">
        <div>
          <div class="section-eyebrow">Worldwide reach</div>
          <h2 class="section-title">
            Tests contributed from
            {{ typeof universityCount === 'number' ? universityCount : 'dozens of' }}
            universities worldwide.
          </h2>
        </div>
      </div>
      <div class="split-7-5">
        <div class="map-frame">
          <overview-map />
        </div>
        <div class="surface surface-pad" style="display: flex; flex-direction: column">
          <div class="video-frame">
            <iframe
              src="https://www.youtube.com/embed/5TkO07T16z4"
              title="Getting started with RESSLab Hub"
              allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen
            ></iframe>
          </div>
          <div style="margin-top: 24px">
            <div class="eyebrow" style="margin-bottom: 10px">Modeling tools</div>
            <p style="margin: 0 0 16px; color: var(--fg-muted); font-size: 14px; line-height: 1.5">
              Beyond data: interactive backbone curves and fragility surfaces for direct use in
              nonlinear analyses.
            </p>
            <div style="display: flex; gap: 8px; flex-wrap: wrap">
              <router-link
                v-for="tool in TOOLS"
                :key="tool.to"
                class="btn btn-secondary btn-sm"
                :to="tool.to"
              >
                {{ tool.name }}
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Partners -->
    <div class="logos">
      <div class="logos-eyebrow">Partners &amp; funding</div>
      <div class="logos-items">
        <a href="https://www.epfl.ch/labs/resslab" target="_blank" rel="noreferrer">
          <img :src="publicPath + 'logo/resslab_logo_v1.svg'" alt="RESSLab" />
        </a>
        <a href="https://www.epfl.ch" target="_blank" rel="noreferrer">
          <img :src="publicPath + 'logo/EPFL_Logo_184X53.svg'" alt="EPFL" />
        </a>
        <a href="https://enac-it4r.epfl.ch" target="_blank" rel="noreferrer">
          <img :src="publicPath + 'logo/logo_IT4R.svg'" alt="ENAC-IT4R" />
        </a>
        <a href="https://www.snf.ch" target="_blank" rel="noreferrer">
          <img
            :src="publicPath + 'logo/SNF_logo_standard_web_color_pos_e.svg'"
            alt="Swiss National Science Foundation"
          />
        </a>
      </div>
    </div>

    <app-footer />
  </div>
</template>
