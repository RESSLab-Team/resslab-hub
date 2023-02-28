<script setup lang="ts">
import { withDefaults, defineProps, ref, computed, defineExpose } from "vue";

export interface CheckBoxDialogItem<K> {
  key: K;
  text: string;
}

// TODO add genericity https://github.com/vuejs/rfcs/discussions/436
type T = string;
const props = withDefaults(
  defineProps<{
    items?: CheckBoxDialogItem<T>[];
    title?: string;
    loadingOnConfirm?: boolean;
  }>(),
  {
    items: () => [],
    title: undefined,
    loadingOnConfirm: false,
  }
);
defineExpose({
  open,
  close,
});

const messageRef = ref<string>();
const dialog = ref<boolean>(false);
const loading = ref<boolean>(false);
const resolveRef = ref<(value: T[] | PromiseLike<T[]>) => void>(() => null);

const values = computed<boolean[]>(() =>
  new Array(props.items.length).fill(true)
);
const hasSelected = computed<boolean>(() =>
  values.value.some((value) => value)
);

function open(message?: string): Promise<T[]> {
  messageRef.value = message;
  loading.value = false;
  dialog.value = true;
  return new Promise((resolve) => {
    resolveRef.value = resolve;
  });
}

function onConfirm(): void {
  const keys: T[] = props.items
    .filter((_, index) => values.value[index])
    .map((item) => item.key);
  resolveRef.value(keys);
  if (props.loadingOnConfirm) {
    loading.value = true;
  } else {
    dialog.value = false;
  }
}

function close(): void {
  dialog.value = false;
}
</script>

<template>
  <v-dialog v-model="dialog" max-width="256">
    <v-card>
      <v-card-title v-if="title">
        {{ title }}
      </v-card-title>
      <v-card-text>
        <span v-if="messageRef">{{ messageRef }}</span>
        <v-checkbox
          v-for="(item, index) in items"
          :key="item.key"
          v-model="values[index]"
          :label="item.text"
          hide-details
        />
      </v-card-text>
      <v-card-actions>
        <v-btn
          color="primary"
          :disabled="!hasSelected"
          :loading="loading"
          text
          @click="onConfirm"
        >
          <v-icon left>mdi-check</v-icon>
          Confirm
        </v-btn>
        <v-btn text @click="close">
          <v-icon left>mdi-close</v-icon>
          Cancel
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
