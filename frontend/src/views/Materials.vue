<template>
  <v-container fluid>
    <v-tabs>
      <v-tab to="/materials/database">Database</v-tab>
      <v-tab to="/materials/model">Material Model</v-tab>
    </v-tabs>
    <router-view></router-view>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from "vue-property-decorator";

@Component
export default class Materials extends Vue {}
</script>
