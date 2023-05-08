<script setup lang="ts">
import AboutContent from '@/components/commons/AboutContent.vue'
import SimpleSnackbar from '@/components/commons/SimpleSnackbar.vue'
import { useNotificationStore } from '@/stores/notification'
import { mdiInformationOutline } from '@mdi/js'
import { ref } from 'vue'

interface MenuItem {
  text: string
  to: string
  children?: MenuItem[]
}

const notificationStore = useNotificationStore()
const subMenuItems: MenuItem[] = [
  {
    text: 'Database',
    to: '/database'
  },
  {
    text: 'Component Model',
    to: '/model'
  },
  {
    text: 'Fragility Curve',
    to: '/fragility-curve'
  }
]
const menuItems: MenuItem[] = [
  {
    text: 'RESSLab Hub',
    to: '/'
  },
  {
    text: 'Connections',
    to: '/connections',
    children: subMenuItems
  },
  {
    text: 'Columns',
    to: '/columns',
    children: subMenuItems
  },
  {
    text: 'Braces',
    to: '/braces',
    children: subMenuItems
  },
  {
    text: 'Materials',
    to: '/materials',
    children: [
      {
        text: 'Database',
        to: '/database'
      },
      {
        text: 'Material Model',
        to: '/model'
      }
    ]
  }
  // {
  //   text: 'Residual Stress',
  //   to: '/residuals',
  //   children: [
  //     {
  //       text: 'Database',
  //       to: '/database'
  //     }
  //   ]
  // }
]

const aboutDialog = ref<boolean>(false)
const snackbar = ref<InstanceType<typeof SimpleSnackbar>>()

notificationStore.$subscribe((_, state) => {
  if (state.message) {
    snackbar.value?.open(state.message, state.url ?? undefined)
  }
})
</script>

<template>
  <v-app>
    <v-app-bar app density="compact">
      <v-tabs color="primary" hide-slider>
        <template v-for="item in menuItems">
          <v-menu v-if="item.children" :key="`${item.to}/`" offset-y open-on-hover>
            <template #activator="{ props }">
              <v-tab :to="item.to" v-bind="props">
                {{ item.text }}
              </v-tab>
            </template>
            <v-list density="compact" nav>
              <v-list-item v-for="subItem in item.children" :key="subItem.to">
                <v-tab
                  :to="item.to + subItem.to"
                  :class="item.to + subItem.to == $route.path ? 'text-primary' : undefined"
                  hide-slider
                >
                  {{ subItem.text }}
                </v-tab>
              </v-list-item>
            </v-list>
          </v-menu>
          <v-tab v-else :key="item.to" :to="item.to">
            <v-app-bar-title v-if="item.to === '/'">
              {{ item.text }}
            </v-app-bar-title>
            <template v-else>
              {{ item.text }}
            </template>
          </v-tab>
        </template>
      </v-tabs>
      <template #append>
        <v-dialog v-model="aboutDialog" max-width="800px">
          <template #activator="{ props }">
            <v-btn v-bind="props" :icon="mdiInformationOutline" />
          </template>
          <about-content @click:close="aboutDialog = false" />
        </v-dialog>
      </template>
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
    <simple-snackbar ref="snackbar" />
  </v-app>
</template>

<style lang="scss" scoped>
.v-toolbar__title {
  overflow: unset;
  text-transform: none;
}

.v-list {
  padding: 0;
  > .v-list-item {
    padding: 0;
    > .v-list-item__content > .v-tab {
      height: 40px;
      width: 100%;
      justify-content: flex-start;
    }
  }
}
</style>
