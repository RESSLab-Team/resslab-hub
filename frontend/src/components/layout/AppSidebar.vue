<script setup lang="ts">
import { useCountsStore } from '@/stores/counts'
import { publicPath } from '@/utils/common'
import { NAV_GROUPS, type NavGroup } from '@/utils/navigation'
import {
  mdiBookOpenVariant,
  mdiChevronDown,
  mdiHomeOutline,
  mdiInformationOutline,
  mdiWeatherNight,
  mdiWeatherSunny
} from '@mdi/js'
import { computed, onMounted, ref } from 'vue'
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

const manuallyOpened = ref(new Set<string>())

function routePrefix(group: NavGroup): string {
  // '/connections/database' -> '/connections'
  return '/' + group.children[0].to.split('/')[1]
}

const activeGroupId = computed(
  () => NAV_GROUPS.find((g) => route.path.startsWith(routePrefix(g) + '/'))?.id
)

function isExpanded(group: NavGroup): boolean {
  return group.id === activeGroupId.value || manuallyOpened.value.has(group.id)
}

function toggleGroup(group: NavGroup) {
  const opened = new Set(manuallyOpened.value)
  if (opened.has(group.id)) opened.delete(group.id)
  else opened.add(group.id)
  manuallyOpened.value = opened
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

    <div class="sidebar-section">Databases &amp; tools</div>
    <template v-for="group in NAV_GROUPS" :key="group.id">
      <!-- Single-page groups render as a plain link -->
      <router-link
        v-if="group.children.length === 1"
        class="sidebar-link"
        :class="{ 'is-active': route.path === group.children[0].to }"
        :to="group.children[0].to"
        @click="emit('close')"
      >
        {{ group.name }}
        <span
          v-if="group.children[0].countId && countsStore.counts[group.children[0].countId] != null"
          class="count"
        >
          {{ countsStore.counts[group.children[0].countId!] }}
        </span>
      </router-link>

      <template v-else>
        <div class="sidebar-group" :class="{ 'is-active': group.id === activeGroupId }">
          <router-link
            class="sidebar-link sidebar-group-link"
            :to="group.children[0].to"
            @click="emit('close')"
          >
            {{ group.name }}
          </router-link>
          <button
            class="sidebar-group-toggle"
            :aria-expanded="isExpanded(group)"
            :aria-label="(isExpanded(group) ? 'Collapse ' : 'Expand ') + group.name"
            @click="toggleGroup(group)"
          >
            <v-icon
              :icon="mdiChevronDown"
              size="16"
              :class="{ 'chevron-open': isExpanded(group) }"
            />
          </button>
        </div>
        <div v-if="isExpanded(group)" class="sidebar-children">
          <router-link
            v-for="child in group.children"
            :key="child.to"
            class="sidebar-link sidebar-child"
            :class="{ 'is-active': route.path === child.to }"
            :to="child.to"
            @click="emit('close')"
          >
            {{ child.name }}
            <span v-if="child.countId && countsStore.counts[child.countId] != null" class="count">
              {{ countsStore.counts[child.countId!] }}
            </span>
          </router-link>
        </div>
      </template>
    </template>

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
