<script setup lang="ts">
import type {
  BraceField,
  ColumnField,
  ConnectionField,
  HSSColumnField,
  MaterialField
} from '@/backend'
import EyebrowText from '@/components/commons/EyebrowText.vue'
import PhotoCarousel from '@/components/home/PhotoCarousel.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import { useCountsStore } from '@/stores/counts'
import { publicPath } from '@/utils/common'
import { DATABASES, TOOLS } from '@/utils/navigation'
import { mdiArrowRight } from '@mdi/js'
import { computed, defineAsyncComponent, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

// Lazy-load the map so leaflet + d3 + markercluster ship in a separate chunk and
// don't block the home page's initial render.
const OverviewMap = defineAsyncComponent(() => import('@/components/map/OverviewMap.vue'))

const { t } = useI18n({ useScope: 'global' })
const countsStore = useCountsStore()

// Lab photos + credits carried over from the pre-redesign home carousel.
const galleryImages = [
  'El Jisr and Lignos (2022)',
  'Elkady and Lignos (2018)',
  'Prof. Dimitrios Lignos, EPFL',
  'Andronikos Skiadopoulos, EPFL',
  'Suzuki and Lignos (2021)',
  'Skiadopoulos and Lignos (2022)',
  'Elkady and Lignos (2018)',
  'Andronikos Skiadopoulos, EPFL'
].map((credit, index) => ({
  src: publicPath + `img/home/Photo${index + 1}.webp`,
  credit
}))
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

onMounted(async () => {
  countsStore.fetch()

  // The API client loads lazily, same as in stores/counts: a static import here
  // would pull axios + the generated client into the home chunk ahead of the
  // first paint, for numbers that only fill in after mount.
  const {
    analyticsApi,
    bracesApi,
    columnsApi,
    connectionsApi,
    hssApi,
    materialsApi,
    residualsApi
  } = await import('@/plugins/axios')

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
    .then(
      (responses) =>
        new Set(responses.flatMap((response) => response.data.map((c) => c.names))).size
    )
    .then((count) => {
      universityCount.value = count
    })

  // Get user count
  analyticsApi
    .getUsers()
    .then((response) => response.data)
    .then((count) => {
      // The backend returns -1 when Google Analytics is unavailable
      // (e.g. no credentials in local dev) — keep the placeholder then.
      if (count >= 0) userCount.value = count.toLocaleString('en-CH')
    })
})
</script>

<template>
  <div>
    <!-- Ultrawide screens (≥2100px) re-lay these blocks via `grid-template-areas`
         (see app.css) — hence the `hp-*` hooks: hero and key numbers full-width
         on top, then databases | map + video in two columns (three from 2400px,
         where the video splits off), with the photo strip and the partners
         strip closing the page. Below that the wrapper is `display: contents`,
         so the page keeps the normal laptop flow in DOM order — databases
         full-width, then the map | video row. -->
    <div class="home-split">
      <!-- Hero — overlapping white text panel breaking the media edge -->
      <section class="hero hp-hero">
        <div class="hero-text">
          <div class="hero-eyebrow"><eyebrow-text text="EPFL · RESSLab" /></div>
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
          <!-- The poster paints the hero immediately; preload=metadata keeps the
             ~1 MB video from competing with the critical CSS/JS/font downloads
             (autoplay still starts the full fetch right after mount). -->
          <video
            autoplay
            loop
            muted
            playsinline
            preload="metadata"
            :poster="publicPath + 'video/steel-mrf-front-page-poster.webp'"
          >
            <source :src="publicPath + 'video/steel-mrf-front-page.mp4'" type="video/mp4" />
          </video>
          <div class="hero-img-credit">RESSLab, EPFL</div>
        </div>
      </section>

      <!-- Key numbers -->
      <div class="keynums hp-kpis">
        <div v-for="(item, index) in keyNumbers" :key="index" class="keynum">
          <div class="keynum-num">{{ item.num }}</div>
          <div class="keynum-bar" />
          <div class="keynum-label">{{ item.label }}</div>
        </div>
      </div>

      <!-- Databases -->
      <section class="section hp-data">
        <div class="section-head">
          <div>
            <div class="section-eyebrow">
              <eyebrow-text :text="t('home.databases.eyebrow')" />
            </div>
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
            <!-- The dashboard's own description; only shown where the tiles have
                 the room for it (the ultrawide column layout). -->
            <p class="cat-tile-desc-long">{{ db.descLong }}</p>
            <div class="cat-tile-meta">
              <template v-if="countsStore.counts[db.id] != null">
                <strong>{{ countsStore.counts[db.id] }}</strong>
                <span>{{ t('home.databases.tests') }}</span>
              </template>
              <template v-if="countsStore.sources[db.id] != null">
                <strong>{{ countsStore.sources[db.id] }}</strong>
                <span>{{ t('home.databases.sources', countsStore.sources[db.id]!) }}</span>
              </template>
              <span style="flex: 1" />
              <span class="cat-tab">{{ db.group }}</span>
            </div>
            <v-icon :icon="mdiArrowRight" size="16" class="cat-arrow" />
          </router-link>
        </div>
      </section>

      <!-- Worldwide reach + tutorial -->
      <section class="section section-bg-subtle hp-reach">
        <div class="section-head">
          <div>
            <div class="section-eyebrow"><eyebrow-text :text="t('home.reach.eyebrow')" /></div>
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
          <!-- Inline styles moved to .tools-panel* in app.css: at ≥2100px this
               panel becomes video-beside-copy, which an inline `display: flex`
               would outrank. -->
          <div class="surface surface-pad tools-panel">
            <div class="video-frame">
              <iframe
                src="https://www.youtube.com/embed/5TkO07T16z4"
                :title="t('home.tools.videoTitle')"
                allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen
              ></iframe>
            </div>
            <div class="tools-panel-copy">
              <div class="eyebrow tools-panel-eyebrow">
                <eyebrow-text :text="t('home.tools.eyebrow')" />
              </div>
              <p class="tools-panel-blurb">{{ t('home.tools.blurb') }}</p>
              <div class="tools-panel-links">
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

      <!-- From the lab -->
      <section class="section hp-gallery">
        <div class="section-head">
          <div>
            <div class="section-eyebrow"><eyebrow-text :text="t('home.gallery.eyebrow')" /></div>
            <h2 class="section-title">{{ t('home.gallery.title') }}</h2>
          </div>
        </div>
        <photo-carousel :images="galleryImages" />
      </section>

      <!-- Partners -->
      <div class="logos hp-partners">
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
    </div>

    <app-footer />
  </div>
</template>
