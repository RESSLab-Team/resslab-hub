<script setup lang="ts">
import { defineProps, defineEmits, computed, withDefaults } from "vue";
import { VContainer } from "vuetify/lib";

interface LegendItem {
  selected: boolean;
  label: string;
  color: string;
  icon: string;
}

interface LegendProps {
  value: LegendItem[];
  separatorsIndex: number[];
}

const getClass = (index: number) => {
  return `legend-checkbox ${
    props.separatorsIndex.includes(index) ? "margin-top" : "no-top-margin"
  }`;
};

const props = withDefaults(defineProps<LegendProps>(), {
  separatorsIndex: () => [],
  value: () => [],
});

const emit = defineEmits(["update:value"]);

const items = computed({
  get() {
    return props.value;
  },
  set(items) {
    emit("update:value", items);
  },
});
</script>

<template>
  <v-container>
    <v-checkbox
      v-for="(item, index) in items"
      :key="index"
      v-model="item.selected"
      :hide-details="true"
      :ripple="false"
      :on-icon="item.icon"
      :off-icon="item.icon"
      :label="item.label"
      :color="item.color"
      :class="getClass(index)"
    />
  </v-container>
</template>

<style lang="scss" scoped>
.legend-checkbox::v-deep .v-icon {
  transition: none;
}

// Transform rectangles into "lines" symbols
.legend-checkbox::v-deep .mdi-rectangle {
  transform: scale(1.3, 0.4);
}

.margin-top {
  margin-top: 15px;
}

.no-top-margin {
  margin-top: 0;
}
</style>
