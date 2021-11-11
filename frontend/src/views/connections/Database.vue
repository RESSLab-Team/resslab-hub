<template>
  <v-row>
    <v-col cols="6">
      <connection-browser></connection-browser>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from "vue-property-decorator";
import ConnectionBrowser from "@/components/ConnectionBrowser.vue";

@Component({
  components: {
    ConnectionBrowser,
  },
})
export default class Home extends Vue {}
</script>
