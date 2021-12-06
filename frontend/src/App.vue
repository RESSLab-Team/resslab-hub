<template>
  <v-app>
    <v-app-bar app dense>
      <v-app-bar-title>
        <div>RESSLab Tools</div>
      </v-app-bar-title>
      <v-tabs>
        <v-tab to="/">Home</v-tab>
        <v-tab to="/connections">Connections</v-tab>
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
