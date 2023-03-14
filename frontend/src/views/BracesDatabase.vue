<script setup lang="ts">
import BraceDashboard from '@/components/braces/BraceDashboard.vue'
import { mdiAlert } from '@mdi/js'
</script>

<template>
  <div>
    <p class="text-center">
      <v-icon :icon="mdiAlert" />
      Section under construction
      <v-icon :icon="mdiAlert" />
    </p>
    <brace-dashboard />
  </div>
</template>
