import { CountModel } from "@/backend";
import { Searches } from "@/utils/common";
import { AxiosResponse } from "axios";
import { Ref, ref, watchEffect } from "vue";
import { Color } from "vuetify/lib/util/colors";

export interface Count {
  name: string;
  value: number;
}

export interface SingleChartProps<F> {
  color?: Color;
  field: F;
  query?: string;
  searches?: Searches;
}
export interface SingleChartEmits {
  (e: "change:searches", key: string, value: string): void;
}

export function useSingleChart<F>(
  field: F,
  query: Ref<string | undefined>,
  getBracesCounts: (
    fields?: F[],
    query?: string
  ) => Promise<AxiosResponse<CountModel[]>>
) {
  const counts = ref<Count[]>([]);

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

  return { counts };
}
