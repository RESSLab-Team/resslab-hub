<template>
  <column-dashboard></column-dashboard>
</template>

<script lang="ts">
import ColumnDashboard from "@/components/column/ColumnDashboard.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    ColumnDashboard,
  },
})
export default class ColumnDatabase extends Vue {}
</script>
