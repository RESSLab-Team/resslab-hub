<template>
  <v-container fluid>
    <v-tabs>
      <v-tab to="/braces/database">Database</v-tab>
      <v-tab to="/braces/component-model">Component Model</v-tab>
      <v-tab to="/braces/fragility-curve">Fragility Curve</v-tab>
    </v-tabs>
    <router-view></router-view>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from "vue-property-decorator";

@Component
export default class Braces extends Vue {}
</script>
