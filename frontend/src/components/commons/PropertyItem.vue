<template>
  <div>
    <span class="text--primary">{{ name }}: </span>
    <slot></slot>
    <template v-if="unit">[{{ unit }}]</template>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from "vue-property-decorator";

@Component
export default class PropertyItem extends Vue {
  @Prop({ type: String })
  readonly name!: string;
  @Prop({ type: String })
  readonly unit: string | undefined;
}
</script>
