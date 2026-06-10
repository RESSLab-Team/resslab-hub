<script setup lang="ts">
import SectionTabs from '@/components/layout/SectionTabs.vue'

const tabs = [
  { label: 'Cyclic Coupons', to: '/materials/cyclic-coupons' },
  { label: 'Tensile Coupons', to: '/materials/tensile-coupons' },
  { label: 'Ductile Fracture', to: '/materials/ductile-fracture' },
  { label: 'Material Model', to: '/materials/model' }
]
</script>

<template>
  <section-tabs :tabs="tabs" />
  <v-container fluid>
    <router-view />
  </v-container>
</template>
