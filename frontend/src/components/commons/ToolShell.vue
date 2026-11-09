<script setup lang="ts">
import PageHeader from '@/components/commons/PageHeader.vue'
import { useEscapeKey } from '@/composables/useEscapeKey'
import { useMediaQuery } from '@/composables/useMediaQuery'
import { mdiClose } from '@mdi/js'
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

/**
 * EPFL design-system scaffold for the interactive tool pages
 * (component models + fragility curves), ported from the layout handoff
 * (handoff_tool_layout/LAYOUT-SPEC.md — the "Rail + Stage" system).
 *
 * The page is height-locked to the viewport: inputs live in a fixed RAIL with
 * its own scroll, results are ONE vertical scroll (chart first). At ≥1600px the
 * results fit the page with no scroll; at ≤899px the rail becomes a right-hand
 * "Parameters" drawer toggled from a trigger under the header.
 *
 * Two layouts:
 *  - `rail`     (default): fixed input rail + results stage. Fill #rail + #stage.
 *  - `parambar` (archetype E): a horizontal parameter bar over full-width
 *    results — few controls, no rail. Fill #parambar + #stage.
 */
withDefaults(
  defineProps<{
    eyebrow: string
    title: string
    /** number shown in the mobile Parameters trigger badge */
    paramCount?: number
    layout?: 'rail' | 'parambar'
    /** archetype modifier on the stage, e.g. 'stage-d' */
    stageClass?: string
  }>(),
  {
    paramCount: undefined,
    layout: 'rail',
    stageClass: undefined
  }
)

/* the Parameters drawer is only reachable at ≤899px */
const paramsOpen = ref(false)
// Same breakpoint as tool-pages.css. Closed, the drawer is `inert`, so Tab
// never lands on inputs nobody can see.
const narrow = useMediaQuery('(max-width: 899px)')
useEscapeKey(paramsOpen, () => (paramsOpen.value = false))

/* close the drawer on navigation, mirroring the app sidebar behaviour */
const route = useRoute()
watch(
  () => route.fullPath,
  () => {
    paramsOpen.value = false
  }
)
</script>

<template>
  <div
    class="tool-page"
    :class="{ 'has-parambar': layout === 'parambar', 'params-open': paramsOpen }"
  >
    <page-header :eyebrow="eyebrow" :title="title">
      <template v-if="$slots.actions" #actions>
        <slot name="actions" />
      </template>
      <slot name="intro" />
    </page-header>

    <div class="tool-body">
      <!-- ── rail layout (default) ─────────────────────────────── -->
      <template v-if="layout === 'rail'">
        <aside class="rail" :inert="(narrow && !paramsOpen) || undefined">
          <div class="drawer-close">
            <span class="dt">{{ $t('tools.common.parameters') }}</span>
            <button class="x" :aria-label="$t('commons.close')" @click="paramsOpen = false">
              <v-icon :icon="mdiClose" size="16" />
            </button>
          </div>
          <slot name="rail" />
        </aside>

        <button
          v-if="paramCount != null"
          class="tool-params-trigger"
          type="button"
          @click="paramsOpen = true"
        >
          {{ $t('tools.common.parameters') }}
          <span class="ct">{{ paramCount }}</span>
        </button>

        <section class="stage" :class="stageClass">
          <slot name="stage" />
        </section>
      </template>

      <!-- ── parambar layout (archetype E) ─────────────────────── -->
      <template v-else>
        <section class="stage e-body">
          <div class="e-parambar">
            <slot name="parambar" />
          </div>
          <div class="e-results" :class="stageClass">
            <slot name="stage" />
          </div>
        </section>
      </template>
    </div>

    <button
      class="tool-scrim"
      type="button"
      :aria-label="$t('commons.close')"
      :inert="!paramsOpen || undefined"
      @click="paramsOpen = false"
    />
  </div>
</template>
