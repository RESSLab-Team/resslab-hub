<template>
  <div>
    <p class="text-center">
      <v-icon>mdi-alert</v-icon>
      Section under construction
      <v-icon>mdi-alert</v-icon>
    </p>
    <brace-dashboard></brace-dashboard>
  </div>
</template>

<script lang="ts">
import BraceDashboard from "@/components/braces/BraceDashboard.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    BraceDashboard,
  },
})
export default class ColumnDatabase extends Vue {}
</script>
