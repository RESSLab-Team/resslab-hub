<script lang="ts">
import { Component, Vue } from "vue-property-decorator";

@Component
export default class CommonDetailMixin extends Vue {
  close(): void {
    this.$emit("close");
  }
}
</script>
