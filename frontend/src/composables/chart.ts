import { CountModel, MatrixModel } from "@/backend";
import { Value } from "@/utils/common";
import { AxiosResponse } from "axios";
import { chain } from "lodash";
import { computed, Ref, ref, watchEffect } from "vue";
import { Color } from "vuetify/lib/util/colors";

export interface Count {
  name: string;
  value: number;
}

export interface ParallelField<T = string> {
  id: T | Division<T>;
  name?: string;
}

export interface Division<T> {
  dividend: T;
  divisor: T;
}

const chartProps = {
  color: Object as () => Color,
  query: String,
};
export interface ChartEmits {
  (e: "change:searches", key: string, value: Value): void;
}

export function singleChartProps<F extends string>() {
  return {
    ...chartProps,
    field: {
      type: String as unknown as () => F,
      required: true,
    },
  };
}

export function useSingleChart<F>(
  emit: ChartEmits,
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

export function parallelChartProps<F extends string>() {
  return {
    ...chartProps,
    fields: {
      type: Array as () => ParallelField<F>[],
      required: true,
    },
  };
}
export function useParallelChart<F extends string>(
  emit: ChartEmits,
  idField: F,
  fields: ParallelField<F>[],
  query: Ref<string | undefined>,
  getMatrix: (
    fields: F[],
    query?: string
  ) => Promise<AxiosResponse<MatrixModel>>
) {
  const ids = ref<string[]>([]);
  const data = ref<(string | number)[][]>([]);

  const requestFields = computed<F[]>(() =>
    chain(fields)
      .flatMap((f) => {
        if (typeof f.id === "string") {
          return [f.id];
        } else {
          return [f.id.dividend, f.id.divisor];
        }
      })
      .uniq()
      .value()
  );

  function changeSearches(value: Value) {
    emit("change:searches", idField, value);
  }

  watchEffect(() => {
    getMatrix(requestFields.value, query.value)
      .then((response) => response.data)
      .then((matrixModel) => {
        ids.value = matrixModel.ids;
        data.value = matrixModel.data as (string | number)[][];
      });
  });

  return { ids, data, requestFields, changeSearches };
}
