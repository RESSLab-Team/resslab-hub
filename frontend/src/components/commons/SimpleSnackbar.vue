<script setup lang="ts">
import { mdiClose } from '@mdi/js'
import { ref } from 'vue'

defineExpose({
  open
})

const snackbar = ref<boolean>(false)
const messageRef = ref<string>('')
const urlRef = ref<string>()

function open(message: string, url?: string): void {
  messageRef.value = message
  urlRef.value = url
  snackbar.value = true
}
</script>

<template>
  <v-snackbar v-model="snackbar">
    <a v-if="urlRef" :href="urlRef">
      {{ messageRef }}
    </a>
    <span v-else>
      {{ messageRef }}
    </span>
    <template #actions>
      <v-btn color="primary" :icon="mdiClose" @click="snackbar = false" />
    </template>
  </v-snackbar>
</template>
