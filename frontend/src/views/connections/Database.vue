<template>
  <connection-dashboard></connection-dashboard>
</template>

<script lang="ts">
import { Component, Vue } from "vue-property-decorator";
import ConnectionDashboard from "@/components/connection/ConnectionDashboard.vue";

@Component({
  components: {
    ConnectionDashboard,
  },
})
export default class ConnectionDatabase extends Vue {}
</script>
