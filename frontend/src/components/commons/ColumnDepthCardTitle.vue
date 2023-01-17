<script setup lang="ts">
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
</script>

<template>
  <v-card-title>
    Column Depth [mm]
    <info-tooltip>
      <p>
        This histogram displays the distribution of column depths in the
        Database.
      </p>
      How to use?
      <ul>
        <li>
          Filter database for specific column depths, by clicking on a bar or
          using the slider below
        </li>
        <li>
          <slot name="how-to-second">
            Filter database depending on the presence of doubler plates welded
            in the panel zone (0/1/2) by clicking on the legend.
          </slot>
        </li>
      </ul>
    </info-tooltip>
  </v-card-title>
</template>
