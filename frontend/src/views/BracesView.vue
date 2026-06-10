<script setup lang="ts">
import SectionTabs from '@/components/layout/SectionTabs.vue'

const tabs = [
  { label: 'Database', to: '/braces/database' },
  { label: 'Fragility Curve', to: '/braces/fragility-curve' }
]
</script>

<template>
  <section-tabs :tabs="tabs" />
  <v-container fluid>
    <router-view />
  </v-container>
</template>
