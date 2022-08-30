<template>
  <brace-fragility></brace-fragility>
</template>

<script lang="ts">
import BraceFragility from "@/components/braces/BraceFragility.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    BraceFragility,
  },
})
export default class BracesFragilityCurve extends Vue {}
</script>
