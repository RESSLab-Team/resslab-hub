<script lang="ts">
import { filterColumnValue, globalSearchKey, Searches } from "@/utils/common";
import { Component, Vue } from "vue-property-decorator";

@Component
export default class DashboardMixin<T> extends Vue {
  search = "";
  searches: Searches = {};
  item: T | null = null;

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
}
</script>
