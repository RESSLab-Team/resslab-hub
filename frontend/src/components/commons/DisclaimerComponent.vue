<template>
  <v-snackbar v-model="snackbarVisible" :timeout="props.timeout" variant="text">
    <v-alert
      :title="$t('commons.alert')"
      type="warning"
      variant="flat"
      density="comfortable"
      closable
    >
      <template #title>
        <slot name="title">
          <v-icon left>{{ mdiInformationOutline }}</v-icon>
        </slot>
      </template>
      <template #text>
        <slot />
      </template>
    </v-alert>
  </v-snackbar>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { mdiInformationOutline } from '@mdi/js'

const props = withDefaults(
  defineProps<{
    timeout?: number
  }>(),
  {
    timeout: 4000
  }
)

const snackbarVisible = ref(true)
</script>
