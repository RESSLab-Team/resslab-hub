import { CountModel } from "@/backend";
import { Page } from "@/utils/backend";
import { Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import download from "downloadjs";
import JSZip from "jszip";
import { computed, Ref, ref, unref, watchEffect } from "vue";
import { DataOptions } from "vuetify";

export enum DownloadType {
  Main = "main",
  Test = "test",
}

export type ColumnType = "text" | "option" | "number" | "boolean";

export interface Column {
  value: string;
  type: ColumnType;
  options?: string[];
  filterOnly?: boolean;
}

export const tableProps = {
  query: String,
  search: String,
  searches: {
    type: Object as () => Searches,
    default: () => ({}),
  },
};
export interface TableEmits<M> {
  (e: "click:row", value: M): void;
  (e: "update:page", value: Page<M>): void;
  (e: "update:search", value: string | undefined): void;
  (e: "update:searches", value: Searches): void;
}
export function useTable<M extends { id: string }, P extends Page<M> = Page<M>>(
  emit: TableEmits<M>,
  name: string,
  query: Ref<string | undefined>,
  searchRef: Ref<string | undefined>,
  searchesRef: Ref<Searches>,
  tests: {
    name: string;
    countKey: keyof M;
    getCsv: (id: string) => Promise<AxiosResponse>;
  }[],
  getCounts: () => Promise<AxiosResponse<CountModel[]>>,
  getPage: (
    query?: string,
    sortBy?: Array<string>,
    sortDesc?: Array<boolean>,
    page?: number,
    size?: number
  ) => Promise<AxiosResponse<P>>,
  getMainCsv: (ids: string[]) => Promise<AxiosResponse>,
  notify: (message: string) => void
) {
  const loading = ref<boolean>(false);
  const items = ref<M[]>([]) as Ref<M[]>;
  const options = ref<DataOptions>();
  const totalCount = ref<number>();
  const totalFilteredCount = ref<number>();

  const search = computed<string | undefined>({
    get: () => searchRef.value,
    set: (value) => emit("update:search", value),
  });
  const searches = computed<Searches>({
    get: () => searchesRef.value,
    set: (value) => emit("update:searches", value),
  });

  function clickRow(item: M) {
    emit("click:row", item);
  }
  function downloadFiles(items: M[], types: DownloadType[]): void {
    const filePromises = [
      types.includes(DownloadType.Main)
        ? [
            getMainCsv(items.map((item) => item.id)).then((response) => ({
              filename: `${name}.csv`,
              content: response.data,
            })),
          ]
        : [],
      types.includes(DownloadType.Test)
        ? tests.flatMap((test) =>
            items
              .filter((item) => (item[test.countKey] as unknown as number) > 0)
              .map((item) => item.id)
              .map((id) =>
                test.getCsv(id).then((response) => ({
                  filename: `${name}-${test.name}-${id}.csv`,
                  content: response.data,
                }))
              )
          )
        : [],
    ].flat();
    Promise.all(filePromises)
      .then((files) => {
        if (files.length === 0) {
          notify("Nothing to download");
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
      .catch((error) => {
        notify(`An error occured : ${error}`);
      });
  }

  getCounts()
    .then((response) => response.data)
    .then((counts) => {
      totalCount.value = counts[0].value;
    });

  watchEffect(() => {
    const optionsValue = unref(options);
    if (optionsValue) {
      loading.value = true;
      getPage(
        query.value,
        optionsValue.sortBy,
        optionsValue.sortDesc,
        optionsValue.page,
        optionsValue.itemsPerPage
      )
        .then((response) => response.data)
        .then((page) => {
          items.value = page.items;
          totalFilteredCount.value = page.total;
          emit("update:page", page);
        })
        .finally(() => {
          loading.value = false;
        });
    }
  });
  return {
    items,
    loading,
    options,
    totalCount,
    totalFilteredCount,
    search,
    searches,
    clickRow,
    downloadFiles,
  };
}
