<template>
  <column-fragility></column-fragility>
</template>

<script lang="ts">
import ColumnFragility from "@/components/columns/ColumnFragility.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    ColumnFragility,
  },
})
export default class ColumnFragilityCurve extends Vue {}
</script>
