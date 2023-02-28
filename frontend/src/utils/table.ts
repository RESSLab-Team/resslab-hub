import { CountModel } from "@/backend";
import { Page } from "@/utils/backend";
import { AxiosResponse } from "axios";
import download from "downloadjs";
import JSZip from "jszip";
import { Ref, ref, unref, watchEffect } from "vue";
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

export function useTable<T extends { id: string }, P extends Page<T> = Page<T>>(
  name: string,
  options: Ref<DataOptions | undefined>,
  query: Ref<string>,
  tests: {
    name: string;
    countKey: keyof T;
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
  const totalCount = ref<number>();
  const loading = ref<boolean>(false);
  const items = ref<T[]>([]) as Ref<T[]>;
  const totalFilteredCount = ref<number>();

  function downloadFiles(items: T[], types: DownloadType[]): void {
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
          // TODO remove ?
          // this.$emit("loadPage", page);
        })
        .finally(() => {
          loading.value = false;
        });
    }
  });
  return {
    totalCount,
    loading,
    items,
    totalFilteredCount,
    downloadFiles,
  };
}
