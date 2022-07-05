<template>
  <v-snackbar v-model="snackbar">
    <a v-if="url" :href="url">
      {{ message }}
    </a>
    <span v-else>
      {{ message }}
    </span>
    <template #action="{ attrs }">
      <v-btn v-bind="attrs" color="primary" icon @click="snackbar = false">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </template>
  </v-snackbar>
</template>

<script lang="ts">
import Vue from "vue";
import Component from "vue-class-component";

@Component
export default class Snackbar extends Vue {
  private snackbar = false;
  private message = "";
  private url: string | null = null;

  public open(message: string, url?: string): void {
    this.message = message;
    this.url = url ?? null;
    this.snackbar = true;
  }
}
</script>
