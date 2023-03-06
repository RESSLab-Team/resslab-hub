import { Page } from "@/utils/backend";
import {
  filterColumnValue,
  globalSearchKey,
  Searches,
  Value,
} from "@/utils/common";
import { computed, ref, triggerRef, unref } from "vue";
import { Route } from "vue-router";

export function useDashboard<M>(route: Route, field: object) {
  const fields: string[] = Object.values(field);

  const search = ref<string>("");
  const searches = ref<Searches>({});
  const item = ref<M>();
  const detail = ref<boolean>(false);

  function clickTableRow(value: M): void {
    item.value = value;
  }
  function closeDetail(): void {
    item.value = undefined;
  }
  function updatePage(page: Page<M>): void {
    if (detail.value && page.total === 1) {
      item.value = page.items[0];
      detail.value = false;
    }
  }
  function changeSearches(key: string, value: Value): void {
    searches.value[key] = value;
    triggerRef(searches);
  }

  const query = computed<string>(() => {
    const queries = Object.entries(searches.value)
      .filter(([, value]) => filterColumnValue(value))
      .map(([key, value]) => `${key}:${value}`);
    const searchValue = unref(search);
    if (searchValue && searchValue.length > 0) {
      queries.push(`%${searchValue}%`);
    }
    return queries.join(";");
  });

  Object.entries(route.query)
    .filter(([key, value]) => fields.includes(key) && value.length > 0)
    .forEach(([key, value]) => {
      searches.value[key] = parseValue(value);
    });
  const globalSearchValue = route.query[globalSearchKey];
  if (typeof globalSearchValue === "string") {
    search.value = globalSearchValue;
  }
  const detailValue = route.query["detail"];
  if (
    detailValue &&
    typeof detailValue === "string" &&
    detailValue.toLowerCase() === "true"
  ) {
    detail.value = true;
  }

  return {
    search,
    searches,
    item,
    query,
    clickTableRow,
    closeDetail,
    updatePage,
    changeSearches,
  };
}

function parseValue(value: string | (string | null)[]): Value {
  if (typeof value === "string") {
    if (value.includes(",")) {
      return value.split(",");
    }
    if (value === "true") {
      return true;
    }
    if (value === "false") {
      return false;
    }
    const numberValue = Number(value);
    if (!isNaN(numberValue)) {
      return numberValue;
    }
    return value;
  } else {
    return value.filter((v) => v !== null);
  }
}
