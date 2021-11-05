<template>
  <v-row>
    <v-col cols="8">
      <specimen-browser></specimen-browser>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from "vue-property-decorator";
import SpecimenBrowser from "@/components/SpecimenBrowser.vue";

@Component({
  components: {
    SpecimenBrowser,
  },
})
export default class Home extends Vue {}
</script>
