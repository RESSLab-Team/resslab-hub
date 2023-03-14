<script setup lang="ts">
import BraceModel from '@/components/braces/BraceModel.vue'
import { mdiAlert } from '@mdi/js'
</script>

<template>
  <div>
    <p class="text-center">
      <v-icon :icon="mdiAlert" />
      Section under construction
      <v-icon :icon="mdiAlert" />
    </p>
    <brace-model />
  </div>
</template>
