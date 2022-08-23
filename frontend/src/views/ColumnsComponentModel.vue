<template>
  <column-component></column-component>
</template>

<script lang="ts">
import ColumnComponent from "@/components/columns/ColumnComponent.vue";
import { Component, Vue } from "vue-property-decorator";

@Component({
  components: {
    ColumnComponent,
  },
})
export default class ColumnsComponentModel extends Vue {}
</script>
