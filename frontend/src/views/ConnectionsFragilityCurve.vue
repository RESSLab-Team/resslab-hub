<template>
  <connection-fragility></connection-fragility>
</template>

<script lang="ts">
import ConnectionFragility from "@/components/connections/ConnectionFragility.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    ConnectionFragility,
  },
})
export default class ConnectionFragilityCurve extends Vue {}
</script>
