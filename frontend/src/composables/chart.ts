import { CountModel } from "@/backend";
import { Value } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Ref, ref, watchEffect } from "vue";
import { Color } from "vuetify/lib/util/colors";

export interface Count {
  name: string;
  value: number;
}

export function singleChartProps<F extends string>() {
  return {
    color: Object as () => Color,
    field: {
      type: String as unknown as () => F,
      required: true,
    },
    query: String,
  };
}
export interface SingleChartEmits {
  (e: "change:searches", key: string, value: Value): void;
}
export function useSingleChart<F>(
  emit: SingleChartEmits,
  field: F,
  query: Ref<string | undefined>,
  getBracesCounts: (
    fields?: F[],
    query?: string
  ) => Promise<AxiosResponse<CountModel[]>>
) {
  const counts = ref<Count[]>([]);

  function changeSearches(key: string, value: Value) {
    emit("change:searches", key, value);
  }

  watchEffect(() => {
    getBracesCounts([field], query.value)
      .then((response) => response.data)
      .then((values) => {
        counts.value = values
          .map((count) => {
            return {
              name: count.names[0],
              value: count.value,
            };
          })
          .sort((c1, c2) => (c1.name < c2.name ? -1 : 1));
      });
  });

  return { counts, changeSearches };
}
