<script lang="ts">
import { Page } from "@/utils/backend";
import { filterColumnValue, globalSearchKey, Searches } from "@/utils/common";
import { Component, Vue } from "vue-property-decorator";

@Component
export default class DashboardMixin<T> extends Vue {
  search = "";
  searches: Searches = {};
  item: T | null = null;
  detail = false;

  get fields(): string[] {
    throw new Error("Should be overriden in children");
  }

  get query(): string {
    const queries = Object.entries(this.searches)
      .filter(([, value]) => filterColumnValue(value))
      .map(([key, value]) => `${key}:${value}`);
    if (this.search && this.search.length > 0) {
      queries.push(`%${this.search}%`);
    }
    return queries.join(";");
  }

  created(): void {
    Object.entries(this.$route.query)
      .filter(([key, value]) => this.fields.includes(key) && value.length > 0)
      .forEach(([key, value]) => {
        this.$set(this.searches, key, this.parseValue(value));
      });
    const globalSearchValue = this.$route.query[globalSearchKey];
    if (typeof globalSearchValue === "string") {
      this.search = globalSearchValue;
    }
    const detailValue = this.$route.query["detail"];
    if (
      detailValue &&
      typeof detailValue === "string" &&
      detailValue.toLowerCase() === "true"
    ) {
      this.detail = true;
    }
  }

  parseValue(
    value: string | (string | null)[]
  ): boolean | number | string | (string | null)[] {
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

  click(item: T): void {
    this.item = item;
  }

  close(): void {
    this.item = null;
  }

  loadPage(page: Page<T>): void {
    if (this.detail && page.total === 1) {
      this.item = page.items[0];
      this.detail = false;
    }
  }
}
</script>
