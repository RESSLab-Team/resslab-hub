<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import SimpleSnackbar from '@/components/commons/SimpleSnackbar.vue'
import { useNotificationStore } from '@/stores/notification'
import { publicPath } from '@/utils/common'
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
  theme.global.name.value = dark.value ? 'dark' : 'light'
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
          <button class="hdr-icon-btn" aria-label="Open navigation" @click="sidebarOpen = true">
            <v-icon :icon="mdiMenu" size="18" />
          </button>
          <router-link class="mhdr-brand" to="/">
            <img :src="publicPath + 'logo/EPFL_Logo_184X53.svg'" alt="EPFL" />
            RESSLab Hub
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
