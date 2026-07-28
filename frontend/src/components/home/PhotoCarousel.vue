<script setup lang="ts">
import { mdiChevronLeft, mdiChevronRight } from '@mdi/js'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * Auto-cycling photo strip for the home page, in the handoff's custom-control
 * style (no Vuetify). Images lazy-load, so the ~1.3 MB gallery only downloads
 * once the section approaches the viewport — never on first paint.
 *
 * The strip shows as many photos side by side as the viewport can carry: one on
 * phones, up to four on a very wide desktop. Arrows and the auto-cycle page by a
 * whole row, so every step reveals a fresh set instead of shuffling one photo
 * along.
 */
const props = defineProps<{ images: { src: string; credit: string }[] }>()

const { t } = useI18n({ useScope: 'global' })

const CYCLE_MS = 5000

// Widest match wins. This is the ONLY place the layout is described: the grid
// and the container cap both read it through custom properties, so there is no
// CSS breakpoint to keep in sync with the paging step. `maxWidth` keeps a pane
// around 500px so photos don't balloon on an ultrawide monitor.
const PANE_TIERS = [
  { query: '(min-width: 2100px)', panes: 4, maxWidth: '1990px' },
  { query: '(min-width: 1600px)', panes: 3, maxWidth: '1500px' },
  { query: '(min-width: 1024px)', panes: 2, maxWidth: '1080px' }
]
const SINGLE_PANE = { panes: 1, maxWidth: '1080px' }

const current = ref(0)
const panes = ref(1)
const maxWidth = ref(SINGLE_PANE.maxWidth)
let timer: number | undefined
let mediaQueries: MediaQueryList[] = []

// Offsets of the photos on screen right now, e.g. [0, 1, 2] for a three-up row.
const offsets = computed(() => Array.from({ length: panes.value }, (_, index) => index))

function isVisible(index: number): boolean {
  return offsets.value.some((offset) => (current.value + offset) % props.images.length === index)
}

function syncPanes(): void {
  const tier = PANE_TIERS.find((candidate) => window.matchMedia(candidate.query).matches)
  const { panes: wanted, maxWidth: width } = tier ?? SINGLE_PANE
  // Never let a row repeat a photo when the gallery is smaller than the row.
  panes.value = Math.max(1, Math.min(wanted, props.images.length))
  maxWidth.value = width
}

function goTo(index: number): void {
  current.value = index
}

function next(): void {
  current.value = (current.value + panes.value) % props.images.length
}

function prev(): void {
  current.value = (current.value - panes.value + props.images.length) % props.images.length
}

function pause(): void {
  window.clearInterval(timer)
  timer = undefined
}

function resume(): void {
  // Auto-advance is motion: skip it entirely under prefers-reduced-motion
  // (the dots still navigate manually).
  if (timer === undefined && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    timer = window.setInterval(next, CYCLE_MS)
  }
}

onMounted(() => {
  mediaQueries = PANE_TIERS.map((tier) => window.matchMedia(tier.query))
  mediaQueries.forEach((query) => query.addEventListener('change', syncPanes))
  syncPanes()
  resume()
})

onBeforeUnmount(() => {
  mediaQueries.forEach((query) => query.removeEventListener('change', syncPanes))
  mediaQueries = []
  pause()
})
</script>

<template>
  <div
    class="pcar"
    :class="{ 'is-single': panes === 1 }"
    :style="{ '--pcar-panes': panes, '--pcar-max': maxWidth }"
    @pointerenter="pause"
    @pointerleave="resume"
  >
    <!-- One pane per photo on screen, each offset a step further into the
         gallery; `panes` comes from the viewport tier. -->
    <div class="pcar-frames">
      <div v-for="offset in offsets" :key="offset" class="pcar-frame">
        <img
          v-for="(image, index) in images"
          :key="image.src"
          :src="image.src"
          :alt="image.credit"
          loading="lazy"
          class="pcar-img"
          :class="{ 'is-active': index === (current + offset) % images.length }"
        />
        <div class="pcar-credit">
          {{
            t('home.gallery.credits', { credit: images[(current + offset) % images.length].credit })
          }}
        </div>
      </div>
    </div>
    <div class="pcar-nav">
      <button
        type="button"
        class="pcar-arrow"
        :aria-label="t('home.gallery.previous')"
        @click="prev"
      >
        <v-icon :icon="mdiChevronLeft" size="18" />
      </button>
      <div class="pcar-dots">
        <button
          v-for="(image, index) in images"
          :key="image.src"
          type="button"
          class="pcar-dot"
          :class="{ 'is-active': isVisible(index) }"
          :aria-label="t('home.gallery.goTo', { n: index + 1 })"
          :aria-pressed="isVisible(index)"
          @click="goTo(index)"
        />
      </div>
      <button type="button" class="pcar-arrow" :aria-label="t('home.gallery.next')" @click="next">
        <v-icon :icon="mdiChevronRight" size="18" />
      </button>
    </div>
  </div>
</template>

<style scoped>
/* `--pcar-panes` / `--pcar-max` are set inline from PANE_TIERS in the script;
   the fallbacks are the single-pane (phone) layout. */
.pcar {
  max-width: var(--pcar-max, 1080px);
  margin: 0 auto;
}
.pcar-frames {
  display: grid;
  grid-template-columns: repeat(var(--pcar-panes, 1), 1fr);
  gap: 16px;
}
.pcar-frame {
  position: relative;
  /* A lone photo reads better wide; once they sit in a row, the squarer 3:2
     keeps each one tall enough to be legible. */
  aspect-ratio: 3 / 2;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-subtle);
}
.pcar.is-single .pcar-frame {
  aspect-ratio: 16 / 9;
}
.pcar-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.6s ease;
}
.pcar-img.is-active {
  opacity: 1;
}
/* Same treatment as .hero-img-credit */
.pcar-credit {
  position: absolute;
  bottom: 14px;
  right: 18px;
  font-size: 11px;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  padding: 3px 8px;
  letter-spacing: 0.02em;
  z-index: 1;
}
.pcar-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  margin-top: 12px;
}
.pcar-arrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--fg-muted);
  cursor: pointer;
  transition: color var(--t-fast);
}
.pcar-arrow:hover {
  color: var(--epfl-red);
}
.pcar-dots {
  display: flex;
  gap: 10px;
  justify-content: center;
}
.pcar-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 0;
  padding: 0;
  background: var(--border-strong);
  cursor: pointer;
  transition: background var(--t-fast);
}
.pcar-dot:hover {
  background: var(--fg-muted);
}
.pcar-dot.is-active {
  background: var(--epfl-red);
}
@media (prefers-reduced-motion: reduce) {
  .pcar-img {
    transition: none;
  }
}
</style>
