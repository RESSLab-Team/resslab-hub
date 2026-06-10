<script setup lang="ts">
import SectionTabs from '@/components/layout/SectionTabs.vue'

const tabs = [
  { label: 'Database', to: '/hss-columns/database' },
  { label: 'Component Model', to: '/hss-columns/model' }
]
</script>

<template>
  <section-tabs :tabs="tabs" />
  <v-container fluid>
    <router-view />
  </v-container>
</template>
