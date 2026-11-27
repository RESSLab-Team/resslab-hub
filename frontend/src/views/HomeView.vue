<script setup lang="ts">
import EyebrowText from '@/components/commons/EyebrowText.vue'
import PhotoCarousel from '@/components/home/PhotoCarousel.vue'
import AppFooter from '@/components/layout/AppFooter.vue'
import { useCountUp } from '@/composables/useCountUp'
import { useCountsStore } from '@/stores/counts'
import { publicPath } from '@/utils/common'
import { kpiSnapshot, type KpiStatus } from '@/utils/kpiSnapshot'
import { databases, tools } from '@/utils/navigation'
import { mdiArrowRight } from '@mdi/js'
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

// Lazy-load the map so maplibre ships in a separate chunk and doesn't block
// the home page's initial render.
const OverviewMap = defineAsyncComponent(() => import('@/components/map/OverviewMap.vue'))

const { t } = useI18n({ useScope: 'global' })
const countsStore = useCountsStore()
// Computed, so the names follow a language switch.
const databaseList = computed(() => databases())
const toolList = computed(() => tools())

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
const reduceMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
const reducedMotion = reduceMotionQuery.matches
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
  { num: databaseList.value.length, label: t('home.keyNumbers.databases'), status: 'live' }
])

// Hero video (#404). The poster is a separate <img> on top of the <video>: a
// `poster` attribute can't be faded, it just vanishes when playback starts,
// which made the hero flicker. The <img> fades out only once the first frame
// is really on screen, so the switch looks like one image.
//
// The src is still attached only on `window` load, so the ~1 MB fetch never
// competes with the first CSS/JS/font/API downloads. `preload="auto"` then
// fetches the first frame right away. `load` fires once per page, so SPA
// re-mounts of Home check readyState instead.
//
// Playback starts from JS (no autoplay attribute), so reduced motion and a
// refused play() keep the poster. A failed load keeps it too: only a displayed
// frame hides it.
const heroVideoSrc = ref<string>()
const heroVideo = ref<HTMLVideoElement>()
const heroBox = ref<HTMLElement>()
const posterHidden = ref(false)
let heroInView = true
let frameCallback: number | undefined
let fallbackRaf: number | undefined

function playHeroVideo(): void {
  const video = heroVideo.value
  if (!video || !heroVideoSrc.value || reduceMotionQuery.matches || !heroInView) return
  // Some frameworks don't map the `muted` attribute to the property, and
  // browsers only autoplay a video that is muted.
  video.muted = true
  video.play().catch(() => {})
}

async function startHeroVideo(): Promise<void> {
  if (reduceMotionQuery.matches) return
  heroVideoSrc.value = publicPath + 'video/steel-mrf-front-page.mp4'
  await nextTick()
  playHeroVideo()
}

// `playing` fires before the frame is painted. requestVideoFrameCallback runs
// once a frame went to the compositor. Without it, wait for currentTime to
// move, then two animation frames so that frame had time to paint.
function onHeroPlaying(): void {
  const video = heroVideo.value
  if (!video || posterHidden.value || frameCallback != null || fallbackRaf != null) return
  // typeof, not `in`: the DOM types say every video has it, so `in` would
  // narrow the fallback branch to never.
  if (typeof video.requestVideoFrameCallback === 'function') {
    frameCallback = video.requestVideoFrameCallback(() => {
      frameCallback = undefined
      posterHidden.value = true
    })
    return
  }
  const waitForTime = () => {
    if (video.currentTime > 0) {
      fallbackRaf = requestAnimationFrame(() => {
        fallbackRaf = requestAnimationFrame(() => {
          fallbackRaf = undefined
          posterHidden.value = true
        })
      })
    } else {
      fallbackRaf = requestAnimationFrame(waitForTime)
    }
  }
  waitForTime()
}

function cancelReveal(): void {
  if (frameCallback != null) heroVideo.value?.cancelVideoFrameCallback(frameCallback)
  if (fallbackRaf != null) cancelAnimationFrame(fallbackRaf)
  frameCallback = undefined
  fallbackRaf = undefined
}

// Reduced motion turned on while playing: stop and show the poster again.
function onReduceMotionChange(): void {
  if (reduceMotionQuery.matches) {
    cancelReveal()
    heroVideo.value?.pause()
    posterHidden.value = false
  } else if (heroVideoSrc.value) {
    playHeroVideo()
  } else {
    startHeroVideo()
  }
}

// Pause the video when the hero leaves the screen, play again when it's back.
let heroObserver: IntersectionObserver | undefined

onMounted(() => {
  if (document.readyState === 'complete') startHeroVideo()
  else window.addEventListener('load', startHeroVideo, { once: true })
  reduceMotionQuery.addEventListener('change', onReduceMotionChange)
  if (heroBox.value && 'IntersectionObserver' in window) {
    heroObserver = new IntersectionObserver(([entry]) => {
      heroInView = entry.isIntersecting
      if (heroInView) playHeroVideo()
      else heroVideo.value?.pause()
    })
    heroObserver.observe(heroBox.value)
  }
})
onBeforeUnmount(() => {
  window.removeEventListener('load', startHeroVideo)
  reduceMotionQuery.removeEventListener('change', onReduceMotionChange)
  heroObserver?.disconnect()
  cancelReveal()
})

onMounted(() => {
  countsStore.fetch()
  countsStore.fetchHomeKpis()
})
</script>

<template>
  <div>
    <!-- Hero — overlapping white text panel breaking the media edge -->
    <section class="hero">
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
      <div ref="heroBox" class="hero-img">
        <!-- Decorative video, started from JS. The <img> poster sits on top and
             fades out once the first frame is shown (see onHeroPlaying). The
             src is deferred to `window` load (see heroVideoSrc). -->
        <video
          ref="heroVideo"
          loop
          muted
          playsinline
          preload="auto"
          aria-hidden="true"
          tabindex="-1"
          disablepictureinpicture
          disableremoteplayback
          :src="heroVideoSrc"
          @playing="onHeroPlaying"
        ></video>
        <img
          class="hero-poster"
          :class="{ 'hero-poster--hidden': posterHidden }"
          :src="publicPath + 'video/steel-mrf-front-page-poster.webp'"
          alt=""
          width="1080"
          height="720"
          fetchpriority="high"
        />
        <div class="hero-img-credit">RESSLab, EPFL</div>
      </div>
    </section>

    <!-- Key numbers -->
    <div class="keynums">
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

    <!-- Databases and tutorial in one row, compact on purpose: the map below
           gets the full width -->
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
          <router-link v-for="db in databaseList" :key="db.id" class="cat-tile" :to="db.to">
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
                v-for="tool in toolList"
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
    <section class="section">
      <div class="section-head">
        <div>
          <div class="section-eyebrow"><eyebrow-text :text="t('home.gallery.eyebrow')" /></div>
          <h2 class="section-title">{{ t('home.gallery.title') }}</h2>
        </div>
      </div>
      <photo-carousel :images="galleryImages" />
    </section>

    <!-- Partners -->
    <div class="logos">
      <div class="logos-eyebrow">{{ t('home.partners.eyebrow') }}</div>
      <div class="logos-items">
        <a href="https://www.epfl.ch/labs/resslab" target="_blank" rel="noopener noreferrer">
          <img :src="publicPath + 'logo/resslab_logo_v1.svg'" alt="RESSLab" />
        </a>
        <a href="https://www.epfl.ch" target="_blank" rel="noopener noreferrer">
          <img :src="publicPath + 'logo/EPFL_Logo_184X53.svg'" alt="EPFL" />
        </a>
        <a href="https://enac-it4r.epfl.ch" target="_blank" rel="noopener noreferrer">
          <img :src="publicPath + 'logo/logo_IT4R.svg'" alt="ENAC-IT4R" />
        </a>
        <a href="https://www.snf.ch" target="_blank" rel="noopener noreferrer">
          <img
            :src="publicPath + 'logo/SNF_logo_standard_web_color_pos_e.svg'"
            alt="Swiss National Science Foundation"
          />
        </a>
        <a href="https://www.swissuniversities.ch" target="_blank" rel="noopener noreferrer">
          <!-- The official SVG has a viewBox but no width or height, so it needs one here. -->
          <img
            :src="publicPath + 'logo/swissuniversities_logo.svg'"
            alt="swissuniversities"
            width="160"
          />
        </a>
      </div>
    </div>

    <app-footer />
  </div>
</template>
