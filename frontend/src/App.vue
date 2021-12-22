<template>
  <v-app>
    <v-app-bar app dense>
      <v-app-bar-title>
        <div>RESSLab Tools</div>
      </v-app-bar-title>
      <v-tabs hide-slider>
        <v-tab to="/">Home</v-tab>
        <v-menu offset-y open-on-hover>
          <template v-slot:activator="{ on, attrs }">
            <v-tab to="/connections" v-bind="attrs" v-on="on">
              Connections
            </v-tab>
          </template>
          <v-list>
            <v-list-item v-for="item in subMenus" :key="item.to">
              <v-tab :to="'/connections' + item.to">{{ item.text }}</v-tab>
            </v-list-item>
          </v-list>
        </v-menu>
        <v-tab to="/columns">Columns</v-tab>
        <v-tab to="/bracings">Bracings</v-tab>
        <v-tab to="/about">About</v-tab>
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
  readonly subMenus: SubMenu[] = [
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
}

interface SubMenu {
  text: string;
  to: string;
}
</script>
