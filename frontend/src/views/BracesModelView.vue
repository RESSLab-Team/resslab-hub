<template>
  <div>
    <p class="text-center">
      <v-icon>mdi-alert</v-icon>
      Section under construction
      <v-icon>mdi-alert</v-icon>
    </p>
    <brace-model></brace-model>
  </div>
</template>

<script lang="ts">
import BraceModel from "@/components/braces/BraceModel.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    BraceModel,
  },
})
export default class BracesModelView extends Vue {}
</script>
