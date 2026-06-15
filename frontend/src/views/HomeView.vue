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
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
const countsStore = useCountsStore()
const universityCount = ref<number | string>('…')
const userCount = ref<number | string>('…')

const keyNumbers = computed(() => [
  {
    num: countsStore.total != null ? countsStore.total.toLocaleString('en-CH') : '…',
    label: t('home.keyNumbers.testsDigitized')
  },
  { num: universityCount.value, label: t('home.keyNumbers.universities') },
  { num: userCount.value, label: t('home.keyNumbers.researchers') },
  { num: DATABASES.length, label: t('home.keyNumbers.databases') }
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
        <h1 class="hero-title">
          <i18n-t keypath="home.hero.title" tag="span" scope="global">
            <template #emphasis
              ><em>{{ t('home.hero.titleEmphasis') }}</em></template
            >
            <template #break><br /></template>
          </i18n-t>
        </h1>
        <p class="hero-lede">{{ t('home.hero.lede') }}</p>
        <div class="hero-cta">
          <router-link class="btn btn-primary" to="/connections/database">
            {{ t('home.hero.browseDatabases') }}
            <v-icon :icon="mdiArrowRight" size="14" />
          </router-link>
          <router-link class="btn btn-secondary" to="/about">
            {{ t('home.hero.aboutProject') }}
          </router-link>
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
          <div class="section-eyebrow">{{ t('home.databases.eyebrow') }}</div>
          <h2 class="section-title">{{ t('home.databases.title') }}</h2>
          <p class="section-sub">{{ t('home.databases.sub') }}</p>
        </div>
        <router-link class="section-link" to="/connections/database">
          {{ t('home.databases.viewAll') }} →
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
              <span>{{ t('home.databases.tests') }}</span>
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
          <div class="section-eyebrow">{{ t('home.reach.eyebrow') }}</div>
          <h2 class="section-title">
            {{
              t('home.reach.title', {
                count:
                  typeof universityCount === 'number' ? universityCount : t('home.reach.dozensOf')
              })
            }}
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
              :title="t('home.tools.videoTitle')"
              allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen
            ></iframe>
          </div>
          <div style="margin-top: 24px">
            <div class="eyebrow" style="margin-bottom: 10px">{{ t('home.tools.eyebrow') }}</div>
            <p style="margin: 0 0 16px; color: var(--fg-muted); font-size: 14px; line-height: 1.5">
              {{ t('home.tools.blurb') }}
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
      <div class="logos-eyebrow">{{ t('home.partners.eyebrow') }}</div>
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
