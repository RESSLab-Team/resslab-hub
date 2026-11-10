<script setup lang="ts">
// An explanatory figure (model sketch, connection type, specimen geometry) that
// opens full size in a dialog on click (#160). Small labels and notation are hard
// to read at the size of a drawer column.
import { mdiClose } from '@mdi/js'
import { computed, ref } from 'vue'
import { useDisplay } from 'vuetify'

const props = withDefaults(
  defineProps<{
    src: string
    alt: string
    maxHeight?: string | number
    caption?: string
  }>(),
  { maxHeight: undefined, caption: undefined }
)
const emit = defineEmits<{ (e: 'error', event: Event): void }>()

const { xs } = useDisplay()
const open = ref(false)

// "Full size" means as big as the screen allows, not the file's own size: the
// specimen SVGs say 140 px wide, smaller than the drawer shows them. The width
// comes from the image ratio, read when the thumbnail loads.
const ratio = ref<number>()
function onLoad(event: Event): void {
  const img = event.target as HTMLImageElement
  if (img.naturalWidth && img.naturalHeight) ratio.value = img.naturalWidth / img.naturalHeight
}
const fullStyle = computed(() =>
  ratio.value ? { width: `min(88vw, calc(80vh * ${ratio.value}))` } : undefined
)

const thumbStyle = computed(() =>
  props.maxHeight === undefined
    ? undefined
    : {
        maxHeight: typeof props.maxHeight === 'number' ? `${props.maxHeight}px` : props.maxHeight
      }
)
</script>

<template>
  <!-- The activator slot gives the button aria-haspopup and aria-expanded, and
       puts the focus back on it when the dialog closes. -->
  <v-dialog v-model="open" width="auto" max-width="none" :fullscreen="xs">
    <template #activator="{ props: activator }">
      <button
        v-bind="activator"
        type="button"
        class="zoom-image"
        :aria-label="$t('commons.zoom_image', { name: alt })"
      >
        <!-- The label is on the button, so the image itself is not read twice. -->
        <img :src="src" alt="" :style="thumbStyle" @load="onLoad" @error="emit('error', $event)" />
      </button>
    </template>
    <v-card class="zoom-card">
      <div class="zoom-head">
        <span class="zoom-title">{{ alt }}</span>
        <v-btn
          :icon="mdiClose"
          :aria-label="$t('commons.close')"
          variant="text"
          density="comfortable"
          @click="open = false"
        />
      </div>
      <div class="zoom-body">
        <img :src="src" :alt="alt" class="zoom-full" :style="fullStyle" />
      </div>
      <div v-if="caption" class="zoom-caption">{{ caption }}</div>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.zoom-image {
  display: block;
  width: 100%;
  padding: 0;
  border: 0;
  background: none;
  cursor: zoom-in;
}
.zoom-image:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}
.zoom-image img {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
  margin: 0 auto;
}

.zoom-card {
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--fg);
}
.zoom-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 8px 8px 16px;
  border-bottom: 1px solid var(--border);
}
.zoom-title {
  flex: 1;
  font-weight: 500;
}
.zoom-body {
  display: flex;
  justify-content: center;
  padding: 16px;
  background: var(--bg);
}
.zoom-full {
  display: block;
  max-width: 88vw;
  max-height: 80vh;
  height: auto;
  object-fit: contain;
}
.zoom-caption {
  /* Wrap to the image width instead of making the dialog as wide as the text. */
  width: 0;
  min-width: 100%;
  padding: 10px 16px;
  border-top: 1px solid var(--border);
  color: var(--fg-muted);
  font-size: 13px;
  line-height: 1.4;
}
</style>
