<template>
  <div>
    <p class="text-center">
      <v-icon>mdi-alert</v-icon>
      Section under construction
      <v-icon>mdi-alert</v-icon>
    </p>
    <column-dashboard></column-dashboard>
  </div>
</template>

<script lang="ts">
import ColumnDashboard from "@/components/columns/ColumnDashboard.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    ColumnDashboard,
  },
})
export default class ColumnDatabase extends Vue {}
</script>
