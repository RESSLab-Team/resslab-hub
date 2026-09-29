<script setup lang="ts">
import EyebrowText from '@/components/commons/EyebrowText.vue'
import PhotoCarousel from '@/components/home/PhotoCarousel.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import { useCountUp } from '@/composables/useCountUp'
import { useCountsStore } from '@/stores/counts'
import { publicPath } from '@/utils/common'
import { kpiSnapshot, type KpiStatus } from '@/utils/kpiSnapshot'
import { DATABASES, TOOLS } from '@/utils/navigation'
import { mdiArrowRight } from '@mdi/js'
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

// Lazy-load the map so maplibre ships in a separate chunk and doesn't block
// the home page's initial render.
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
// KPI values live in the counts store, seeded from the committed snapshot
// (see utils/kpiSnapshot.ts) — overlaid with this session's cached live
// values — so the key numbers render on first paint; the live fetches
// overwrite them. Each KPI's status drives the bar under its number:
// ping-ponging while the live fetch is in flight, muted + tooltip when it
// failed and the snapshot stays. Displayed values go through useCountUp so a
// live number that differs from the seed counts into place instead of jumping.

// The loading class is only dropped on an `animationiteration` boundary —
// each keyframe cycle is a full left-right round trip, so even a fetch that
// resolves instantly shows one clean trip before the bar settles. Reduced
// motion runs no animation (and fires no events), so it skips straight to
// the settled state. KPIs already loaded earlier this session (store fetched,
// or hydrated from the session cache after a reload) skip the bar entirely —
// their numbers are already the live ones.
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
const barAnimating = ref([
  !reducedMotion && !countsStore.hydrated.counts && countsStore.countsStatus === 'loading',
  !reducedMotion &&
    !countsStore.hydrated.universities &&
    countsStore.universitiesStatus === 'loading',
  !reducedMotion && !countsStore.hydrated.users && countsStore.usersStatus === 'loading',
  false
])

function onBarCycle(index: number): void {
  if (keyNumbers.value[index].status !== 'loading') {
    barAnimating.value[index] = false
  }
}

// Displayed values hold the snapshot number while the bar is still animating,
// then count up to the live value in a single tween once it has settled —
// this also keeps the total from wobbling as its nine counts land one by one.
const initialTotal = countsStore.total
const displayedTotal = useCountUp(() => (barAnimating.value[0] ? initialTotal : countsStore.total))
const displayedUniversities = useCountUp(() =>
  barAnimating.value[1] ? kpiSnapshot.universities : countsStore.universities
)
const displayedUsers = useCountUp(() =>
  barAnimating.value[2] ? kpiSnapshot.users : countsStore.users
)

const keyNumbers = computed<{ num: number | string; label: string; status: KpiStatus }[]>(() => [
  {
    num: displayedTotal.value != null ? displayedTotal.value.toLocaleString('en-CH') : '…',
    label: t('home.keyNumbers.testsDigitized'),
    status: countsStore.countsStatus
  },
  {
    num: displayedUniversities.value ?? '…',
    label: t('home.keyNumbers.universities'),
    status: countsStore.universitiesStatus
  },
  {
    num: displayedUsers.value != null ? displayedUsers.value.toLocaleString('en-CH') : '…',
    label: t('home.keyNumbers.researchers'),
    status: countsStore.usersStatus
  },
  { num: DATABASES.length, label: t('home.keyNumbers.databases'), status: 'live' }
])

// The hero <video> renders poster-only until the page has fully loaded, so its
// ~1 MB fetch never competes with the initial CSS/JS/font/API traffic: the src
// is only attached on `window` load, and autoplay+muted picks it up from there.
// `load` fires once per page, so SPA re-mounts of Home check readyState instead.
const heroVideoSrc = ref<string>()
const heroVideo = ref<HTMLVideoElement>()
const startHeroVideo = async () => {
  heroVideoSrc.value = publicPath + 'video/steel-mrf-front-page.mp4'
  await nextTick()
  // Reinforce the autoplay attribute: an explicit play() is the documented
  // path for sources attached after mount. Rejections (e.g. hidden tab, where
  // the browser defers playback until visible) are fine — autoplay takes over.
  heroVideo.value?.play().catch(() => {})
}
onMounted(() => {
  if (document.readyState === 'complete') startHeroVideo()
  else window.addEventListener('load', startHeroVideo, { once: true })
})
onBeforeUnmount(() => window.removeEventListener('load', startHeroVideo))

onMounted(() => {
  countsStore.fetch()
  countsStore.fetchHomeKpis()
})
</script>

<template>
  <div>
    <!-- Ultrawide screens (≥2100px) re-lay these blocks via `grid-template-areas`
         (see app.css), hence the `hp-*` hooks: hero and key numbers full-width
         on top, then two columns (databases and video on the left, the map on
         the right, wider), with the photo strip and the partners strip closing
         the page. Below that the wrapper is `display: contents`, so the page
         keeps the normal flow in DOM order: databases and video, then the map
         full-width. -->
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
          <!-- The poster paints the hero immediately; the src is deferred to
             `window` load (see heroVideoSrc) so the ~1 MB video never competes
             with the critical CSS/JS/font/API downloads. -->
          <video
            ref="heroVideo"
            autoplay
            loop
            muted
            playsinline
            preload="none"
            :src="heroVideoSrc"
            :poster="publicPath + 'video/steel-mrf-front-page-poster.webp'"
          ></video>
          <div class="hero-img-credit">RESSLab, EPFL</div>
        </div>
      </section>

      <!-- Key numbers -->
      <div class="keynums hp-kpis">
        <div
          v-for="(item, index) in keyNumbers"
          :key="index"
          class="keynum"
          :title="
            item.status === 'stale'
              ? t('home.keyNumbers.staleTooltip', { date: kpiSnapshot.generatedAt })
              : undefined
          "
        >
          <div class="keynum-num">{{ item.num }}</div>
          <div
            class="keynum-bar"
            :class="{
              'keynum-bar--loading': barAnimating[index],
              'keynum-bar--stale': item.status === 'stale'
            }"
            @animationiteration="onBarCycle(index)"
          />
          <div class="keynum-label">{{ item.label }}</div>
        </div>
      </div>

      <!-- Databases + tutorial: compact on purpose, the map below gets the room -->
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
        <div class="data-split">
          <div class="cat-grid">
            <router-link v-for="db in DATABASES" :key="db.id" class="cat-tile" :to="db.to">
              <div class="cat-tile-icon"><v-icon :icon="db.icon" size="18" /></div>
              <h3 class="cat-tile-title">{{ db.name }}</h3>
              <p class="cat-tile-desc">{{ db.desc }}</p>
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
          <div class="surface tools-panel">
            <div class="video-frame">
              <!-- loading=lazy: the YouTube embed pulls hundreds of kB of
                   third-party player assets, and this panel sits below the
                   fold — don't fetch any of it until the user scrolls near. -->
              <iframe
                src="https://www.youtube.com/embed/5TkO07T16z4"
                :title="t('home.tools.videoTitle')"
                loading="lazy"
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

      <!-- Worldwide reach -->
      <section class="section section-bg-subtle hp-reach">
        <div class="section-head">
          <div>
            <div class="section-eyebrow"><eyebrow-text :text="t('home.reach.eyebrow')" /></div>
            <h2 class="section-title">
              {{
                t('home.reach.title', {
                  count: countsStore.universities ?? t('home.reach.dozensOf')
                })
              }}
            </h2>
          </div>
        </div>
        <div class="map-frame">
          <overview-map />
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
