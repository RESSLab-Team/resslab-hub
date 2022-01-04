<script lang="ts">
import { primaryColor } from "@/utils/vuetify";
import { Component, Prop, Vue } from "vue-property-decorator";
import { Color } from "vuetify/lib/util/colors";

@Component
export default class SliderParent extends Vue {
  @Prop({ type: Object as () => Color, default: () => primaryColor })
  readonly color: Color | undefined;

  get baseColor(): string | undefined {
    return this.color?.base;
  }

  get lightenColor(): string | undefined {
    return this.color?.lighten4;
  }

  get darkenColor(): string | undefined {
    return this.color?.darken4;
  }
}
</script>
