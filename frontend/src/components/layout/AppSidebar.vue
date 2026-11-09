<script setup lang="ts">
import BrandMark from '@/components/layout/BrandMark.vue'
import LanguageToggle from '@/components/layout/LanguageToggle.vue'
import { useAuthStore } from '@/stores/auth'
import { useCountsStore } from '@/stores/counts'
import { useFeaturesStore } from '@/stores/features'
import { NAV_GROUPS, type NavGroup } from '@/utils/navigation'
import {
  mdiBookOpenVariant,
  mdiChevronDown,
  mdiClipboardCheckOutline,
  mdiHomeOutline,
  mdiInformationOutline,
  mdiLoginVariant,
  mdiShieldAccountOutline,
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
const auth = useAuthStore()
const features = useFeaturesStore()
onMounted(() => {
  countsStore.fetch()
  // Hidden until the answer is in, so a deployment that switched the pipeline
  // off never flashes its links (CONTRIBUTIONS_ENABLED, docs/releasing.md).
  features.ensureLoaded()
  // The account block needs the answer, and the sidebar is on every page, so
  // this is where the one /auth/me call gets made for anonymous browsing too.
  auth.ensureLoaded()
})

const initials = computed(() => {
  const name = auth.user?.display_name || auth.user?.email || ''
  return (
    name
      .split(/[\s@.]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('') || '?'
  )
})

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

// The count a group row shows, folded or open: the sum of its databases
// (Materials has three). Undefined until every one of them has a value.
function groupCount(group: NavGroup): number | undefined {
  const ids = group.children.flatMap((child) => (child.countId ? [child.countId] : []))
  if (ids.length === 0) return undefined
  const values = ids.map((id) => countsStore.counts[id])
  if (values.some((value) => value == null)) return undefined
  return values.reduce<number>((sum, value) => sum + (value ?? 0), 0)
}

// A "Database" child would only repeat the count of its group row, so a
// child shows its own count only when the group sums several (Materials).
function hasSeveralDatabases(group: NavGroup): boolean {
  return group.children.filter((child) => child.countId).length > 1
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
      <brand-mark />
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
        <span v-if="groupCount(group) != null" class="count">{{ groupCount(group) }}</span>
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
            <span v-if="groupCount(group) != null" class="count">{{ groupCount(group) }}</span>
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
            <span
              v-if="
                child.countId &&
                countsStore.counts[child.countId] != null &&
                hasSeveralDatabases(group)
              "
              class="count"
            >
              {{ countsStore.counts[child.countId!] }}
            </span>
          </router-link>
        </div>
      </template>
    </template>

    <template v-if="features.contributions">
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

      <!-- The queue is for curators only (#248). -->
      <template v-if="auth.hasRole('curator')">
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
      </template>

      <div class="sidebar-section">{{ $t('auth.account.section') }}</div>
      <router-link
        v-if="auth.isAuthenticated"
        class="sidebar-link account-link"
        :class="{ 'is-active': route.path === '/account' }"
        to="/account"
        @click="emit('close')"
      >
        <span class="account-avatar">{{ initials }}</span>
        <span class="account-text">
          <span class="account-name">{{ auth.user?.display_name || auth.user?.email }}</span>
          <span class="account-role">{{ $t(`auth.roles.${auth.user?.role ?? 'viewer'}`) }}</span>
        </span>
      </router-link>
      <router-link
        v-else
        class="sidebar-link"
        :class="{ 'is-active': route.path.startsWith('/login') }"
        :to="{ name: 'Login', query: { next: route.fullPath } }"
        @click="emit('close')"
      >
        <v-icon :icon="mdiLoginVariant" size="16" />
        {{ $t('auth.login.sign_in') }}
      </router-link>
      <router-link
        v-if="auth.hasRole('admin')"
        class="sidebar-link"
        :class="{ 'is-active': route.path.startsWith('/admin') }"
        to="/admin"
        @click="emit('close')"
      >
        <v-icon :icon="mdiShieldAccountOutline" size="16" />
        {{ $t('admin.nav') }}
      </router-link>
    </template>

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
      rel="noopener noreferrer"
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
