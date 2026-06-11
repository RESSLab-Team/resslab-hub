<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <v-container fluid :class="{ 'pa-0': route.path === '/connections/database' }">
    <router-view />
  </v-container>
</template>
