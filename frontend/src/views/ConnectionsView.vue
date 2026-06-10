<script setup lang="ts">
import SectionTabs from '@/components/layout/SectionTabs.vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const tabs = [
  { label: 'Database', to: '/connections/database' },
  { label: 'Component Model', to: '/connections/model' },
  { label: 'Fragility Curve', to: '/connections/fragility-curve' }
]
</script>

<template>
  <section-tabs :tabs="tabs" />
  <v-container fluid :class="{ 'pa-0': route.path === '/connections/database' }">
    <router-view />
  </v-container>
</template>
