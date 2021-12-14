<template>
  <v-dialog v-model="dialog" max-width="256">
    <v-card>
      <v-card-title>
        {{ title }}
      </v-card-title>
      <v-card-text>
        <span v-if="message">{{ message }}</span>
        <v-checkbox
          v-for="(item, index) in items"
          :key="item.key"
          v-model="values[index]"
          :label="item.text"
          hide-details
        ></v-checkbox>
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

<script lang="ts">
import { Component, Prop, Vue } from "vue-property-decorator";

@Component
export default class CheckboxDialog<K> extends Vue {
  @Prop({ type: Array as () => CheckBoxDialogItem<K>[] })
  private readonly items!: CheckBoxDialogItem<K>[];
  @Prop({ type: String, default: "" })
  private readonly title!: string;
  @Prop({ type: Boolean, default: false })
  private readonly loadingOnConfirm!: boolean;

  private message: string | null = null;
  private dialog = false;
  private loading = false;
  private values: boolean[] = [];
  private resolve: (value: K[] | PromiseLike<K[]>) => void = () => null;

  private get hasSelected(): boolean {
    return this.values.some((value) => value);
  }

  private created(): void {
    this.values = new Array(this.items.length).fill(true);
  }

  public open(message?: string): Promise<K[]> {
    this.message = message ?? null;
    this.loading = false;
    this.dialog = true;
    return new Promise((resolve) => {
      this.resolve = resolve;
    });
  }

  private onConfirm(): void {
    const keys: K[] = this.items
      .filter((_, index) => this.values[index])
      .map((item) => item.key);
    this.resolve(keys);
    if (this.loadingOnConfirm) {
      this.loading = true;
    } else {
      this.dialog = false;
    }
  }

  public close(): void {
    this.dialog = false;
  }
}

export interface CheckBoxDialogItem<K> {
  key: K;
  text: string;
}
</script>
