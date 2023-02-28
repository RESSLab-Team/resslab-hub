<script setup lang="ts">
import { ref, defineExpose } from "vue";

defineExpose({
  open,
});

const snackbar = ref<boolean>(false);
const messageRef = ref<string>("");
const urlRef = ref<string>();

function open(message: string, url?: string): void {
  messageRef.value = message;
  urlRef.value = url;
  snackbar.value = true;
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
    <template #action="{ attrs }">
      <v-btn v-bind="attrs" color="primary" icon @click="snackbar = false">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </template>
  </v-snackbar>
</template>
