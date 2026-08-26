<script setup lang="ts">
import { mdiInformationOutline } from '@mdi/js'

/** `interactive` keeps the tooltip open while the pointer is inside it, for content with a link. */
defineProps<{ interactive?: boolean }>()
</script>

<template>
  <v-tooltip :interactive="interactive" location="bottom" max-width="512">
    <template #activator="{ props }">
      <v-icon class="px-1" v-bind="props" :icon="mdiInformationOutline" />
    </template>
    <slot />
  </v-tooltip>
</template>
