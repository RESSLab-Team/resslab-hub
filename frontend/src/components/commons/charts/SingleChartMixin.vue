<script lang="ts">
import SingleChart from "@/components/commons/charts/SingleChart.vue";
import { Searches } from "@/utils/common";
import { Component, Prop, PropSync, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component({
  components: {
    SingleChart,
  },
})
export default class SingleChartMixin<T> extends Vue {
  @Prop({ type: Object as () => Color })
  readonly color: Color | undefined;
  @Prop({ type: String as unknown as () => T })
  readonly field!: T;
  @Prop({ type: String })
  readonly query: string | undefined;
  @PropSync("searches", { type: Object as () => Searches })
  fieldSearches: Searches | undefined;
}
</script>
