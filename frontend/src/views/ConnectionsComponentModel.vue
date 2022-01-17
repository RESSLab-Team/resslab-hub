<template>
  <connection-component></connection-component>
</template>

<script lang="ts">
import ConnectionComponent from "@/components/connections/ConnectionComponent.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    ConnectionComponent,
  },
})
export default class ConnectionComponentModel extends Vue {}
</script>
