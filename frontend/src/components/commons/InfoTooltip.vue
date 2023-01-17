<template>
  <v-tooltip bottom max-width="512">
    <template #activator="{ on, attrs }">
      <v-icon class="px-1" v-bind="attrs" v-on="on">
        mdi-information-outline
      </v-icon>
    </template>
    <slot></slot>
  </v-tooltip>
</template>
