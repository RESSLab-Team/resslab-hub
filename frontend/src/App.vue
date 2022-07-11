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
                <v-tab :to="item.to + subItem.to">{{ subItem.text }}</v-tab>
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
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script lang="ts">
import { Component, Vue } from "vue-property-decorator";

@Component
export default class App extends Vue {
  readonly subMenuItems: MenuItem[] = [
    {
      text: "Database",
      to: "/database",
    },
    {
      text: "Component Model",
      to: "/component-model",
    },
    {
      text: "Fragility Curve",
      to: "/fragility-curve",
    },
  ];
  readonly menuItems: MenuItem[] = [
    {
      text: "RESSLab Hub",
      to: "/",
    },
    {
      text: "Connections",
      to: "/connections",
      children: this.subMenuItems,
    },
    {
      text: "Columns",
      to: "/columns",
      children: this.subMenuItems,
    },
    {
      text: "Braces",
      to: "/braces",
      children: this.subMenuItems,
    },
    {
      text: "About",
      to: "/about",
    },
  ];
}

interface MenuItem {
  text: string;
  to: string;
  children?: MenuItem[];
}
</script>

<style lang="scss" scoped>
.v-toolbar__title {
  overflow: unset;
  text-transform: none;
}
</style>
