<script setup lang="ts">
import { useCountsStore } from '@/stores/counts'
import { publicPath } from '@/utils/common'
import { DATABASES, TOOLS } from '@/utils/navigation'
import {
  mdiBookOpenVariant,
  mdiHomeOutline,
  mdiInformationOutline,
  mdiWeatherNight,
  mdiWeatherSunny
} from '@mdi/js'
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'

defineProps<{
  open: boolean
  dark: boolean
}>()
const emit = defineEmits<{
  (e: 'toggle-theme'): void
  (e: 'close'): void
}>()

const route = useRoute()
const countsStore = useCountsStore()
onMounted(() => countsStore.fetch())

const components = DATABASES.filter((db) => db.group === 'components')
const materials = DATABASES.filter((db) => db.group === 'materials')

function isActive(to: string): boolean {
  return route.path === to
}
</script>

<template>
  <aside class="sidebar" :class="{ open }">
    <router-link class="sidebar-brand" to="/" @click="emit('close')">
      <img :src="publicPath + 'logo/EPFL_Logo_184X53.svg'" alt="EPFL" />
      <div class="sidebar-brand-name">RESSLab Hub<small>Steel structures research</small></div>
    </router-link>

    <router-link
      class="sidebar-link"
      :class="{ 'is-active': route.path === '/' }"
      to="/"
      @click="emit('close')"
    >
      <v-icon :icon="mdiHomeOutline" size="16" />
      Overview
    </router-link>

    <div class="sidebar-section">Components</div>
    <router-link
      v-for="db in components"
      :key="db.id"
      class="sidebar-link"
      :class="{ 'is-active': isActive(db.to) }"
      :to="db.to"
      @click="emit('close')"
    >
      {{ db.name }}
      <span v-if="countsStore.counts[db.id] != null" class="count">
        {{ countsStore.counts[db.id] }}
      </span>
    </router-link>

    <div class="sidebar-section">Materials</div>
    <router-link
      v-for="db in materials"
      :key="db.id"
      class="sidebar-link"
      :class="{ 'is-active': isActive(db.to) }"
      :to="db.to"
      @click="emit('close')"
    >
      {{ db.name }}
      <span v-if="countsStore.counts[db.id] != null" class="count">
        {{ countsStore.counts[db.id] }}
      </span>
    </router-link>

    <div class="sidebar-section">Modeling tools</div>
    <router-link
      v-for="tool in TOOLS"
      :key="tool.to"
      class="sidebar-link"
      :class="{ 'is-active': isActive(tool.to) }"
      :to="tool.to"
      @click="emit('close')"
    >
      {{ tool.name }}
    </router-link>

    <div class="sidebar-section">Reference</div>
    <router-link
      class="sidebar-link"
      :class="{ 'is-active': route.path === '/about' }"
      to="/about"
      @click="emit('close')"
    >
      <v-icon :icon="mdiInformationOutline" size="16" />
      About &amp; credits
    </router-link>
    <a
      class="sidebar-link"
      href="https://github.com/RESSLab-Team/resslab-hub"
      target="_blank"
      rel="noreferrer"
    >
      <v-icon :icon="mdiBookOpenVariant" size="16" />
      Documentation
    </a>

    <div class="sidebar-foot">
      <button
        class="hdr-icon-btn"
        :title="dark ? 'Switch to light mode' : 'Switch to dark mode'"
        :aria-label="dark ? 'Switch to light mode' : 'Switch to dark mode'"
        @click="emit('toggle-theme')"
      >
        <v-icon :icon="dark ? mdiWeatherSunny : mdiWeatherNight" size="16" />
      </button>
      <span>© EPFL · RESSLab</span>
    </div>
  </aside>
</template>
