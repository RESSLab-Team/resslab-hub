<script lang="ts">
import { Page } from "@/utils/backend";
import { Component, Vue } from "vue-property-decorator";

@Component
export default class SimpleTableMixin<T> extends Vue {
  click(item: T): void {
    this.$emit("click", item);
  }

  loadPage(page: Page<T>): void {
    this.$emit("loadPage", page);
  }
}
</script>
