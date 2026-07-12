<script setup lang="ts">
import { mdiChevronLeft, mdiChevronRight } from '@mdi/js'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * Auto-cycling photo strip for the home page, in the handoff's custom-control
 * style (no Vuetify). Images lazy-load, so the ~1.3 MB gallery only downloads
 * once the section approaches the viewport — never on first paint.
 */
const props = defineProps<{ images: { src: string; credit: string }[] }>()

const { t } = useI18n({ useScope: 'global' })

const CYCLE_MS = 5000

// Must match the .pcar-frame-secondary breakpoint below: when both panes are
// visible, arrows and the auto-cycle page by two so each step shows a fresh
// pair instead of shuffling one photo across.
const TWO_UP_QUERY = '(min-width: 1024px)'

const current = ref(0)
let timer: number | undefined

function step(): number {
  return window.matchMedia(TWO_UP_QUERY).matches ? 2 : 1
}

function goTo(index: number): void {
  current.value = index
}

function next(): void {
  current.value = (current.value + step()) % props.images.length
}

function prev(): void {
  current.value = (current.value - step() + props.images.length) % props.images.length
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

onMounted(resume)
onBeforeUnmount(pause)
</script>

<template>
  <div class="pcar" @pointerenter="pause" @pointerleave="resume">
    <!-- Two panes offset by one image: wide screens show the pair side by
         side, the second pane collapses away below the breakpoint. -->
    <div class="pcar-frames">
      <div
        v-for="offset in [0, 1]"
        :key="offset"
        class="pcar-frame"
        :class="{ 'pcar-frame-secondary': offset === 1 }"
      >
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
          :class="{ 'is-active': index === current }"
          :aria-label="t('home.gallery.goTo', { n: index + 1 })"
          :aria-pressed="index === current"
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
.pcar {
  max-width: 1080px;
  margin: 0 auto;
}
.pcar-frames {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}
.pcar-frame {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-subtle);
}
.pcar-frame-secondary {
  display: none;
}
/* Breakpoint mirrored by TWO_UP_QUERY in the script. */
@media (min-width: 1024px) {
  .pcar-frames {
    grid-template-columns: 1fr 1fr;
  }
  .pcar-frame {
    aspect-ratio: 3 / 2;
  }
  .pcar-frame-secondary {
    display: block;
  }
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
