<template>
  <v-card>
    <v-card-title>
      <slot name="title">
        {{ title }}
      </slot>
      <v-spacer></v-spacer>
      <v-text-field
        v-model="globalSearch"
        clearable
        hide-details
        single-line
        append-icon="mdi-magnify"
        label="Search"
      ></v-text-field>
      <v-btn color="primary" :disabled="!hasFilters" text @click="resetFilters">
        Reset filters
      </v-btn>
    </v-card-title>
    <v-data-table
      v-model="selectedItems"
      dense
      :headers="tableHeaders"
      :items="items"
      :items-per-page="5"
      :footer-props="{
        itemsPerPageOptions: [5, 10, 20, 100, 1000],
      }"
      :loading="loading"
      must-sort
      :options.sync="options"
      :search="search"
      :server-items-length="totalFilteredCount"
      show-select
      :sort-by="tableHeaders[0].value"
      @click:row="click"
    >
      <template #top>
        <v-row class="px-4 pb-4">
          <v-col v-for="header in filterHeaders" :key="header.value">
            <v-select
              v-if="header.options"
              v-model="columnSearches[header.value]"
              clearable
              hide-details
              :label="header.text"
              :multiple="header.multiple"
              :items="header.options"
            >
            </v-select>
            <div v-else v-switch="header.type">
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'text'"
                clearable
                hide-details
                :label="header.text"
              ></v-text-field>
              <v-select
                v-model="columnSearches[header.value]"
                v-case="'boolean'"
                clearable
                hide-details
                :label="header.text"
                :items="booleanOptions"
              ></v-select>
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'number'"
                clearable
                hide-details
                hide-spin-buttons
                :label="header.text"
                type="number"
              ></v-text-field>
            </div>
          </v-col>
        </v-row>
      </template>
      <template #[`body.prepend`]>
        <tr>
          <td>
            <!-- select -->
            <v-icon>mdi-magnify</v-icon>
          </td>
          <td v-for="header in tableHeaders" :key="header.value">
            <v-select
              v-if="header.options"
              v-model="columnSearches[header.value]"
              class="mt-0 pt-0"
              clearable
              hide-details
              :label="header.text"
              :multiple="header.multiple"
              :items="header.options"
              single-line
            >
              <template #item="{ item, on, attrs }">
                <slot
                  :name="`column.header.item.${header.value}`"
                  :item="item"
                  :on="on"
                  :attrs="attrs"
                ></slot>
              </template>
            </v-select>
            <div v-else v-switch="header.type">
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'text'"
                class="mt-0 pt-0"
                clearable
                hide-details
                :label="header.text"
                single-line
              ></v-text-field>
              <v-select
                v-model="columnSearches[header.value]"
                v-case="'boolean'"
                class="mt-0 pt-0"
                clearable
                hide-details
                :label="header.text"
                :items="booleanOptions"
                single-line
              ></v-select>
              <v-text-field
                v-model="columnSearches[header.value]"
                v-case="'number'"
                class="mt-0 pt-0"
                clearable
                hide-details
                hide-spin-buttons
                :label="header.text"
                single-line
                type="number"
              ></v-text-field>
            </div>
          </td>
        </tr>
      </template>
      <template #[`item.t_dp_tot`]="{ item }">
        <template v-if="item.t_dp_tot">{{ item.t_dp_tot }}</template>
      </template>
    </v-data-table>
    <v-card-actions>
      <v-btn
        color="primary"
        :disabled="
          selectedItems.length === 0 || selectedItems.length > maxDownloadCount
        "
        text
        @click="downloadZip"
      >
        <v-icon left>mdi-download</v-icon>
        Download ({{ selectedItems.length }}/{{ totalCount }})
      </v-btn>
      <v-btn color="primary" :disabled="!hasFilters" text @click="shareUrl">
        <v-icon left>mdi-share</v-icon>
        Share
      </v-btn>
    </v-card-actions>
    <snackbar ref="snackbar"></snackbar>
    <checkbox-dialog
      ref="downloadDialog"
      title="Download"
      :items="checkboxDialogItems"
      loading-on-confirm
    ></checkbox-dialog>
  </v-card>
</template>

<script lang="ts">
import { CountModel } from "@/backend";
import CheckboxDialog, {
  CheckBoxDialogItem,
} from "@/components/commons/CheckboxDialog.vue";
import InfoTooltip from "@/components/commons/InfoTooltip.vue";
import Snackbar from "@/components/commons/Snackbar.vue";
import { Page } from "@/utils/backend";
import { filterColumnValue, globalSearchKey, Searches } from "@/utils/common";
import { booleanOptions } from "@/utils/vuetify";
import { AxiosResponse } from "axios";
import download from "downloadjs";
import JSZip from "jszip";
import { Component, Prop, PropSync, Vue, Watch } from "vue-property-decorator";
import { DataOptions, DataTableHeader } from "vuetify";

@Component({
  components: {
    InfoTooltip,
    Snackbar,
    CheckboxDialog,
  },
})
export default class SimpleTable<T, P extends Page<T>> extends Vue {
  $refs!: {
    downloadDialog: CheckboxDialog<DownloadType>;
    snackbar: Snackbar;
  };
  readonly booleanOptions = booleanOptions;
  readonly maxDownloadCount = 5;

  @Prop({ type: String, default: "" })
  readonly title!: string;
  @Prop({ type: Array as () => Column[], default: () => [] })
  readonly columns!: Column[];
  @Prop({ type: Function })
  readonly getCounts!: () => Promise<AxiosResponse<CountModel[]>>;
  @Prop({ type: Function })
  readonly getPage!: (
    query?: string,
    sortBy?: Array<string>,
    sortDesc?: Array<boolean>,
    page?: number,
    size?: number
  ) => Promise<AxiosResponse<P>>;
  @Prop({ type: Function })
  readonly getFiles!: (
    selectedItems: T[],
    types: DownloadType[]
  ) => Promise<DownloadFile[]>;
  @Prop({ type: String, default: "" })
  readonly prefix!: string;
  @Prop({ default: "" })
  readonly query!: string;
  @PropSync("searches", { type: Object as () => Searches, default: () => ({}) })
  columnSearches!: Searches;
  @PropSync("search", { type: String, default: () => "" })
  globalSearch!: string;

  readonly checkboxDialogItems: CheckBoxDialogItem<DownloadType>[] = [
    {
      key: DownloadType.Main,
      text: "Master data",
    },
    {
      key: DownloadType.Test,
      text: "Test data",
    },
  ];

  items: T[] = [];
  totalFilteredCount = -1;
  loading = true;
  options: DataOptions | null = null;
  selectedItems: T[] = [];
  totalCount = -1;

  get tableHeaders(): TableHeader[] {
    return this.columns
      .filter((column) => !column.filterOnly)
      .map(this.getTableHeader);
  }

  get filterHeaders(): TableHeader[] {
    return this.columns
      .filter((column) => column.filterOnly)
      .map(this.getTableHeader);
  }

  get hasFilters(): boolean {
    return (
      this.globalSearch.length > 0 ||
      Object.values(this.columnSearches).filter(filterColumnValue).length > 0
    );
  }

  get snackbar(): Snackbar {
    return this.$refs.snackbar;
  }

  get downloadDialog(): CheckboxDialog<DownloadType> {
    return this.$refs.downloadDialog;
  }

  created(): void {
    this.getCounts()
      .then((response) => response.data)
      .then((counts) => {
        this.totalCount = counts[0].value;
      });
  }

  @Watch("options", { deep: true })
  @Watch("query")
  onTableChanged(): void {
    if (this.options) {
      this.loading = true;
      this.getPage(
        this.query,
        this.options.sortBy,
        this.options.sortDesc,
        this.options.page,
        this.options.itemsPerPage
      )
        .then((response) => response.data)
        .then((page) => {
          this.items = page.items;
          this.totalFilteredCount = page.total;
          this.$emit("loadPage", page);
        })
        .finally(() => {
          this.loading = false;
        });
    }
  }

  @Watch("selectedItems")
  onSelectedItemsChanged(): void {
    if (this.selectedItems.length > this.maxDownloadCount) {
      this.snackbar.open(
        `You cannot download more than ${this.maxDownloadCount} items.`
      );
    }
  }

  getTableHeader(column: Column): TableHeader {
    return {
      value: column.value,
      text: this.$t(this.prefix + column.value).toString(),
      type: column.type,
      options: column.options?.sort(),
      multiple: column.options ? column.options.length > 2 : false,
    };
  }

  resetFilters(): void {
    this.globalSearch = "";
    this.columnSearches = {};
  }

  click(item: T): void {
    this.$emit("click", item);
  }

  /**
   * Open download dialog for option selection, get files from backend, zip them and download the zip
   */
  downloadZip(): void {
    this.downloadDialog
      .open(`${this.selectedItems.length} selected`)
      .then((types) => this.getFiles(this.selectedItems, types))
      .then((files) => {
        if (files.length === 0) {
          this.snackbar.open("Nothing to download");
          return null;
        }
        const zip = new JSZip();
        files.forEach((file) => {
          zip.file(file.filename, file.content);
        });
        return zip.generateAsync({ type: "blob" });
      })
      .then((content) => {
        if (content) {
          download(
            content,
            `export-${new Date().getTime()}.zip`,
            "application/zip"
          );
        }
      })
      .finally(() => {
        this.downloadDialog.close();
      });
  }

  shareUrl(): void {
    const url = new URL(window.location.origin + this.$route.path);
    Object.entries(this.columnSearches)
      .filter(([, value]) => filterColumnValue(value))
      .forEach(([key, value]) => {
        url.searchParams.append(key, value.toString());
      });
    if (this.globalSearch.length > 0) {
      url.searchParams.append(globalSearchKey, this.globalSearch);
    }
    const shareUrl = url.href;
    if (navigator.share) {
      navigator.share({
        url: shareUrl,
      });
      return;
    }
    if (navigator.clipboard) {
      navigator.clipboard.writeText(shareUrl);
      this.snackbar.open("Copied to clipboard");
      return;
    }
    this.snackbar.open(shareUrl, shareUrl);
  }
}

export type ColumnType = "text" | "option" | "number" | "boolean";

export interface Column {
  value: string;
  type: ColumnType;
  options?: string[];
  filterOnly?: boolean;
}

export enum DownloadType {
  Main = "main",
  Test = "test",
}

export interface DownloadFile {
  filename: string;
  content: string;
}

interface TableHeader extends DataTableHeader {
  type: ColumnType;
  options?: string[];
  multiple?: boolean;
}
</script>

<style lang="scss" scoped>
:deep(.v-data-table__wrapper) > table > tbody > tr:hover {
  cursor: pointer;
}
</style>
