<script setup lang="ts">
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
</script>

<template>
  <v-card-title>
    Steel Material Type
    <info-tooltip>
      <p>
        This rectangle below displays the proportion of each steel material in
        the database. Steel materials are defined according to the respective
        region of origin.
      </p>
      How to use?
      <ul>
        <li>
          See the available steel materials and by hovering over the
          corresponding material in the rectangle you can see how many tests are
          available per steel material type
        </li>
        <li>
          Filter the Database for a specific steel material type by clicking on
          a rectangle or by using the dates sliders
        </li>
      </ul>
    </info-tooltip>
  </v-card-title>
</template>
