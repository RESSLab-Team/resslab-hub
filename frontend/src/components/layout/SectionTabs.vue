<script setup lang="ts">
import { useRoute } from 'vue-router'

defineProps<{
  tabs: { label: string; to: string }[]
}>()

const route = useRoute()
</script>

<template>
  <nav class="section-tabs">
    <div class="dash-tabs">
      <router-link
        v-for="tab in tabs"
        :key="tab.to"
        class="dash-tab"
        :class="{ on: route.path === tab.to }"
        :to="tab.to"
      >
        {{ tab.label }}
      </router-link>
    </div>
  </nav>
</template>
