<template>
  <connection-dashboard></connection-dashboard>
</template>

<script lang="ts">
import ConnectionDashboard from "@/components/connections/ConnectionDashboard.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    ConnectionDashboard,
  },
})
export default class ConnectionDatabase extends Vue {}
</script>
