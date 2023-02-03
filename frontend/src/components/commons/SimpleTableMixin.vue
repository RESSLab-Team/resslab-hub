<script lang="ts">
import {
  DownloadFile,
  DownloadType,
} from "@/components/commons/SimpleTable.vue";
import { Page } from "@/utils/backend";
import { AxiosResponse } from "axios";
import { Component, Vue } from "vue-property-decorator";

@Component
export default class SimpleTableMixin<T extends { id: string }> extends Vue {
  click(item: T): void {
    this.$emit("click", item);
  }

  loadPage(page: Page<T>): void {
    this.$emit("loadPage", page);
  }

  async getDownloadFiles(
    selectedItems: T[],
    types: DownloadType[],
    name: string,
    getMainCsv: (ids: string[]) => Promise<AxiosResponse>,
    ...tests: {
      name: string;
      countKey: keyof T;
      getCsv: (id: string) => Promise<AxiosResponse>;
    }[]
  ): Promise<DownloadFile[]> {
    const filePromises: Promise<DownloadFile>[] = [
      types.includes(DownloadType.Main)
        ? [
            getMainCsv(selectedItems.map((item) => item.id)).then(
              (response) => ({
                filename: `${name}.csv`,
                content: response.data,
              })
            ),
          ]
        : [],
      types.includes(DownloadType.Test)
        ? tests.flatMap((test) =>
            selectedItems
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
    return Promise.all(filePromises);
  }
}
</script>
