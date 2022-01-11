<template>
  <v-container fluid>
    <v-tabs>
      <v-tab to="/columns/database">Database</v-tab>
      <v-tab to="/columns/component-model">Component Model</v-tab>
      <v-tab to="/columns/fragility-curve">Fragility Curve</v-tab>
    </v-tabs>
    <router-view></router-view>
  </v-container>
</template>
