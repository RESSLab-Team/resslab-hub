<script lang="ts">
import DoubleChart from "@/components/commons/charts/DoubleChart.vue";
import { Searches } from "@/utils/common";
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component({
  components: {
    DoubleChart,
  },
})
export default class DoubleChartMixin<T> extends Vue {
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;
  @Prop({ type: Array as () => T[] })
  readonly fields!: [T, T];
  @Prop({ type: String })
  readonly query: string | undefined;
  @Prop({ type: String })
  readonly type: string | undefined;
  @PropSync("searches", { type: Object as () => Searches })
  fieldSearches: Searches | undefined;
}
</script>
