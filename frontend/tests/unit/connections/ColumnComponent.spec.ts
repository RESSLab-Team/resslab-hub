import ColumnComponent from "@/components/columns/ColumnComponent.vue";
import { shallowMount } from "@vue/test-utils";

describe("ColumnComponent.vue", () => {
  it("aisc - W4x13", async () => {
    const radPrecision = 1;
    const mmPrecision = -1;

    const wrapper = shallowMount<ColumnComponent>(ColumnComponent);
    await wrapper.setData({
      section: {
        id: "W4x13",
        bf: 103.124,
        h: 75.438,
        tf: 8.763,
        tw: 7.112,
        ix: 4703415.10928,
        zx: 102255.27936,
        ry: 25.4,
        d: 105.664,
      },
      pgPye: 0.2,
      l: 5000,
      lb: 5000,
      fy: 379.225,
    });

    expect(wrapper.vm.ke).toBeCloseTo(1157040, mmPrecision);
    expect(wrapper.vm.my).toBeCloseTo(40134, mmPrecision);

    expect(wrapper.vm.backbone.mc).toBeCloseTo(40134, mmPrecision);
    expect(wrapper.vm.backbone.alpha).toBeCloseTo(0, radPrecision);
    expect(wrapper.vm.backbone.alphaPc).toBeCloseTo(
      -0.301909128782995,
      radPrecision
    );
    expect(wrapper.vm.backbone.lambda).toBeCloseTo(3, radPrecision);

    expect(wrapper.vm.envelope.mc).toBeCloseTo(52175, mmPrecision);
    expect(wrapper.vm.envelope.alpha).toBeCloseTo(
      0.242693789510631,
      radPrecision
    );
    expect(wrapper.vm.envelope.alphaPc).toBeCloseTo(
      -0.604686389947832,
      radPrecision
    );
  });
});
