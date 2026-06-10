<script setup lang="ts">
import SectionTabs from '@/components/layout/SectionTabs.vue'

const tabs = [
  { label: 'Database', to: '/columns/database' },
  { label: 'Component Model', to: '/columns/model' },
  { label: 'Fragility Curve', to: '/columns/fragility-curve' }
]
</script>

<template>
  <section-tabs :tabs="tabs" />
  <v-container fluid>
    <router-view />
  </v-container>
</template>
