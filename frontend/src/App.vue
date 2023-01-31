<script setup lang="ts">
import { ref } from "vue";
import AboutContent from "./components/commons/AboutContent.vue";

interface MenuItem {
  text: string;
  to: string;
  children?: MenuItem[];
}

const subMenuItems: MenuItem[] = [
  {
    text: "Database",
    to: "/database",
  },
  {
    text: "Component Model",
    to: "/model",
  },
  {
    text: "Fragility Curve",
    to: "/fragility-curve",
  },
];
const menuItems: MenuItem[] = [
  {
    text: "RESSLab Hub",
    to: "/",
  },
  {
    text: "Connections",
    to: "/connections",
    children: subMenuItems,
  },
  {
    text: "Columns",
    to: "/columns",
    children: subMenuItems,
  },
  {
    text: "Braces",
    to: "/braces",
    children: subMenuItems,
  },
  {
    text: "Materials",
    to: "/materials",
    children: [
      {
        text: "Database",
        to: "/database",
      },
      {
        text: "Material Model",
        to: "/model",
      },
    ],
  },
];

const aboutDialog = ref<boolean>(false);
</script>

<template>
  <v-app>
    <v-app-bar app dense>
      <v-tabs hide-slider>
        <template v-for="item in menuItems">
          <v-menu v-if="item.children" :key="item.to" offset-y open-on-hover>
            <template #activator="{ on, attrs }">
              <v-tab :to="item.to" v-bind="attrs" v-on="on">
                {{ item.text }}
              </v-tab>
            </template>
            <v-list>
              <v-list-item v-for="subItem in item.children" :key="subItem.to">
                <v-tab
                  :to="item.to + subItem.to"
                  :class="
                    item.to + subItem.to == $route.path
                      ? 'primary--text'
                      : undefined
                  "
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
        <v-spacer></v-spacer>
        <v-dialog v-model="aboutDialog" max-width="800px">
          <template #activator="{ on, attrs }">
            <v-tab v-bind="attrs" v-on="on">
              <v-icon>mdi-information-outline</v-icon>
            </v-tab>
          </template>
          <about-content @click:close="aboutDialog = false" />
        </v-dialog>
      </v-tabs>
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<style lang="scss" scoped>
.v-toolbar__title {
  overflow: unset;
  text-transform: none;
}
</style>
