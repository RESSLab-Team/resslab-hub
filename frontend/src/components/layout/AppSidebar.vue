<script setup lang="ts">
import LanguageToggle from '@/components/layout/LanguageToggle.vue'
import { useCountsStore } from '@/stores/counts'
import { NAV_GROUPS, type NavGroup } from '@/utils/navigation'
import {
  mdiBookOpenVariant,
  mdiChevronDown,
  mdiClipboardCheckOutline,
  mdiHomeOutline,
  mdiInformationOutline,
  mdiUploadOutline,
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
      <svg
        class="brand-mark"
        viewBox="0 0 48 48"
        fill="none"
        stroke-linecap="butt"
        stroke-linejoin="miter"
        aria-hidden="true"
      >
        <path d="M11.95 4.00 L11.95 44.00" stroke-width="0.85" stroke="currentColor" />
        <path d="M14.05 4.00 L14.05 44.00" stroke-width="0.85" stroke="currentColor" />
        <path d="M11.95 4.00 L14.05 4.00" stroke-width="0.85" stroke="currentColor" />
        <path d="M11.95 44.00 L14.05 44.00" stroke-width="0.85" stroke="currentColor" />
        <path d="M33.95 4.00 L33.95 44.00" stroke-width="0.85" stroke="currentColor" />
        <path d="M36.05 4.00 L36.05 44.00" stroke-width="0.85" stroke="currentColor" />
        <path d="M33.95 4.00 L36.05 4.00" stroke-width="0.85" stroke="currentColor" />
        <path d="M33.95 44.00 L36.05 44.00" stroke-width="0.85" stroke="currentColor" />
        <path d="M5.00 13.05 L43.00 13.05" stroke-width="0.85" stroke="currentColor" />
        <path d="M5.00 10.95 L43.00 10.95" stroke-width="0.85" stroke="currentColor" />
        <path d="M5.00 13.05 L5.00 10.95" stroke-width="0.85" stroke="currentColor" />
        <path d="M43.00 13.05 L43.00 10.95" stroke-width="0.85" stroke="currentColor" />
        <path d="M5.00 37.05 L43.00 37.05" stroke-width="0.85" stroke="currentColor" />
        <path d="M5.00 34.95 L43.00 34.95" stroke-width="0.85" stroke="currentColor" />
        <path d="M5.00 37.05 L5.00 34.95" stroke-width="0.85" stroke="currentColor" />
        <path d="M43.00 37.05 L43.00 34.95" stroke-width="0.85" stroke="currentColor" />
        <path d="M14.05 13.05 L33.95 34.95" stroke-width="0.6" stroke="var(--epfl-red)" />
        <path d="M33.95 13.05 L14.05 34.95" stroke-width="0.6" stroke="var(--epfl-red)" />
        <path
          d="M25.90 24.00 A1.9 1.9 0 1 1 25.90 24.00 Z"
          stroke-width="0.6"
          stroke="var(--epfl-red)"
        />
        <circle cx="13.00" cy="9.60" r="0.55" fill="currentColor" stroke="none" />
        <circle cx="13.00" cy="14.40" r="0.55" fill="currentColor" stroke="none" />
        <circle cx="13.00" cy="33.60" r="0.55" fill="currentColor" stroke="none" />
        <circle cx="13.00" cy="38.40" r="0.55" fill="currentColor" stroke="none" />
        <circle cx="35.00" cy="9.60" r="0.55" fill="currentColor" stroke="none" />
        <circle cx="35.00" cy="14.40" r="0.55" fill="currentColor" stroke="none" />
        <circle cx="35.00" cy="33.60" r="0.55" fill="currentColor" stroke="none" />
        <circle cx="35.00" cy="38.40" r="0.55" fill="currentColor" stroke="none" />
      </svg>
      <div class="sidebar-brand-name">
        RESSLab <span class="brand-hub">Hub</span
        ><small>{{ $t('shell.brand_tagline') }} · EPFL</small>
      </div>
    </router-link>

    <router-link
      class="sidebar-link"
      :class="{ 'is-active': route.path === '/' }"
      to="/"
      @click="emit('close')"
    >
      <v-icon :icon="mdiHomeOutline" size="16" />
      {{ $t('shell.overview') }}
    </router-link>

    <div class="sidebar-section">{{ $t('shell.databases_and_tools') }}</div>
    <template v-for="group in NAV_GROUPS" :key="group.id">
      <!-- Single-page groups render as a plain link -->
      <router-link
        v-if="group.children.length === 1"
        class="sidebar-link"
        :class="{ 'is-active': route.path === group.children[0].to }"
        :to="group.children[0].to"
        @click="emit('close')"
      >
        <v-icon :icon="group.icon" size="16" />
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
            <v-icon :icon="group.icon" size="16" />
            {{ group.name }}
          </router-link>
          <button
            class="sidebar-group-toggle"
            :aria-expanded="isExpanded(group)"
            :aria-label="
              isExpanded(group)
                ? $t('shell.collapse_group', { group: group.name })
                : $t('shell.expand_group', { group: group.name })
            "
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
            <v-icon v-if="child.icon" :icon="child.icon" size="15" />
            {{ child.name }}
            <span v-if="child.countId && countsStore.counts[child.countId] != null" class="count">
              {{ countsStore.counts[child.countId!] }}
            </span>
          </router-link>
        </div>
      </template>
    </template>

    <div class="sidebar-section">{{ $t('shell.contribute') }}</div>
    <router-link
      class="sidebar-link"
      :class="{ 'is-active': route.path.startsWith('/contribute') }"
      to="/contribute/new"
      @click="emit('close')"
    >
      <v-icon :icon="mdiUploadOutline" size="16" />
      {{ $t('contribute.new_submission') }}
    </router-link>

    <div class="sidebar-section">{{ $t('curation.eyebrow') }}</div>
    <router-link
      class="sidebar-link"
      :class="{ 'is-active': route.path.startsWith('/curation') }"
      to="/curation"
      @click="emit('close')"
    >
      <v-icon :icon="mdiClipboardCheckOutline" size="16" />
      {{ $t('curation.nav.review_queue') }}
    </router-link>

    <div class="sidebar-section">{{ $t('shell.reference') }}</div>
    <router-link
      class="sidebar-link"
      :class="{ 'is-active': route.path === '/about' }"
      to="/about"
      @click="emit('close')"
    >
      <v-icon :icon="mdiInformationOutline" size="16" />
      {{ $t('shell.about_and_credits') }}
    </router-link>
    <a
      class="sidebar-link"
      href="https://github.com/RESSLab-Team/resslab-hub"
      target="_blank"
      rel="noreferrer"
    >
      <v-icon :icon="mdiBookOpenVariant" size="16" />
      {{ $t('shell.documentation') }}
    </a>

    <div class="sidebar-foot">
      <button
        class="hdr-icon-btn"
        :title="dark ? $t('shell.switch_to_light') : $t('shell.switch_to_dark')"
        :aria-label="dark ? $t('shell.switch_to_light') : $t('shell.switch_to_dark')"
        @click="emit('toggle-theme')"
      >
        <v-icon :icon="dark ? mdiWeatherSunny : mdiWeatherNight" size="16" />
      </button>
      <language-toggle />
      <span>© EPFL · RESSLab</span>
    </div>
  </aside>
</template>
