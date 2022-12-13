<template>
  <div>
    <p class="text-center">
      <v-icon>mdi-alert</v-icon>
      Section under construction
      <v-icon>mdi-alert</v-icon>
    </p>
    <material-dashboard></material-dashboard>
  </div>
</template>

<script lang="ts">
import MaterialDashboard from "@/components/materials/MaterialDashboard.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    MaterialDashboard,
  },
})
export default class MaterialDatabase extends Vue {}
</script>
