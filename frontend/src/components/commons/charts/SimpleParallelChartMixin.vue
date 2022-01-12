<script lang="ts">
import SimpleParallelChart, {
  ParallelField,
} from "@/components/commons/charts/SimpleParallelChart.vue";
import { Searches } from "@/utils/common";
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component({
  components: {
    SimpleParallelChart,
  },
})
export default class SimpleParallelChartMixin<T> extends Vue {
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;
  @Prop({ type: Array as () => T[] })
  readonly fields!: ParallelField<T>[];
  @Prop({ type: String })
  readonly query: string | undefined;
  @PropSync("searches", { type: Object as () => Searches })
  fieldSearches: Searches | undefined;
}
</script>
