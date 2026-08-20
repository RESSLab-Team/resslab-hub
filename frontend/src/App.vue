<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import SimpleSnackbar from '@/components/commons/SimpleSnackbar.vue'
import { useNotificationStore } from '@/stores/notification'
import { mdiMenu } from '@mdi/js'
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from 'vuetify'

const notificationStore = useNotificationStore()
const snackbar = ref<InstanceType<typeof SimpleSnackbar>>()

notificationStore.$subscribe((_, state) => {
  if (state.message) {
    snackbar.value?.open(state.message, state.url ?? undefined)
  }
})

/* ---- theme (light default, dark persisted) ---- */
const THEME_STORAGE_KEY = 'THEME'
const theme = useTheme()
const dark = ref(localStorage.getItem(THEME_STORAGE_KEY) === 'dark')

function applyTheme(): void {
  theme.change(dark.value ? 'dark' : 'light')
  document.body.classList.toggle('theme-dark', dark.value)
}
function toggleTheme(): void {
  dark.value = !dark.value
  localStorage.setItem(THEME_STORAGE_KEY, dark.value ? 'dark' : 'light')
  applyTheme()
}
onMounted(applyTheme)

/* ---- mobile sidebar ---- */
const sidebarOpen = ref(false)
const route = useRoute()
watch(
  () => route.fullPath,
  () => {
    sidebarOpen.value = false
  }
)
</script>

<template>
  <v-app>
    <div class="app-shell">
      <app-sidebar
        :open="sidebarOpen"
        :dark="dark"
        @toggle-theme="toggleTheme"
        @close="sidebarOpen = false"
      />
      <div class="sidebar-scrim" :class="{ open: sidebarOpen }" @click="sidebarOpen = false" />
      <div class="app-main">
        <header class="mhdr">
          <button
            class="hdr-icon-btn"
            :aria-label="$t('shell.open_navigation')"
            @click="sidebarOpen = true"
          >
            <v-icon :icon="mdiMenu" size="18" />
          </button>
          <router-link class="mhdr-brand" to="/">
            <svg
              class="brand-mark"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-linecap="butt"
              stroke-linejoin="miter"
              aria-hidden="true"
            >
              <path d="M6.5 2.5V21.5M17.5 2.5V21.5M2.5 6.5H21.5M2.5 17.5H21.5" stroke-width="2.2" />
              <path d="M6.5 6.5L17.5 17.5M17.5 6.5L6.5 17.5" stroke-width="1.6" />
            </svg>
            <span class="mhdr-brand-name"
              >RESSLab <span class="brand-hub">Hub</span
              ><small>{{ $t('shell.brand_tagline') }} · EPFL</small></span
            >
          </router-link>
        </header>
        <main class="app-content">
          <router-view />
        </main>
      </div>
    </div>
    <simple-snackbar ref="snackbar" />
  </v-app>
</template>
