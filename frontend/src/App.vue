<template>
  <v-app>
    <v-app-bar app dense>
      <v-app-bar-title>
        <div>RESSLab Hub</div>
      </v-app-bar-title>
      <v-tabs hide-slider>
        <template v-for="item in menuItems">
          <v-menu v-if="item.children" :key="item.to" offset-y open-on-hover>
            <template v-slot:activator="{ on, attrs }">
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
          <v-tab v-else :key="item.to" :to="item.to">{{ item.text }}</v-tab>
        </template>
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
}
</style>

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
      text: "Home",
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
      text: "Bracings",
      to: "/bracings",
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
