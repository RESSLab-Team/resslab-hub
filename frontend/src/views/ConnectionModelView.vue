<template>
  <connection-model></connection-model>
</template>

<script lang="ts">
import ConnectionModel from "@/components/connections/ConnectionModel.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    ConnectionModel,
  },
})
export default class ConnectionModelView extends Vue {}
</script>
