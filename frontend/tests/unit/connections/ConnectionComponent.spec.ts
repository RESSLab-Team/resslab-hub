import ConnectionModel from "@/components/connections/ConnectionModel.vue";
import { shallowMount } from "@vue/test-utils";

describe("ConnectionModel.vue", () => {
  it("aisc - W36X150", async () => {
    const radPrecision = 4;
    const mmPrecision = 0;

    const wrapper = shallowMount<ConnectionModel>(ConnectionModel);
    await wrapper.setData({
      section: {
        id: "W36X150",
        bf: 304.8,
        h: 826.008,
        tf: 23.876,
        tw: 15.875,
        ix: 3762732087.424,
        zx: 9520884.184,
        ry: 62.738,
        d: 911.86,
      },
      rbsReduction: 0.5,
      l: 8000,
      lb: 4000,
      fy: 379.211635,
    });

    expect(wrapper.vm.ke).toBeCloseTo(578520058, mmPrecision);

    expect(wrapper.vm.backboneRbs.my).toBeCloseTo(2528265, mmPrecision);
    expect(wrapper.vm.backboneRbs.thetaY).toBeCloseTo(
      0.004370228904778947,
      radPrecision
    );
    expect(wrapper.vm.backboneRbs.thetaP).toBeCloseTo(
      0.0162860835082784,
      radPrecision
    );

    expect(wrapper.vm.backboneNonRbs.my).toBeCloseTo(4224203, mmPrecision);
    expect(wrapper.vm.backboneNonRbs.thetaY).toBeCloseTo(
      0.007301740201213988,
      radPrecision
    );
    expect(wrapper.vm.backboneNonRbs.thetaP).toBeCloseTo(
      0.01645703935241783,
      radPrecision
    );

    expect(wrapper.vm.envelopeRbs.my).toBeCloseTo(2528265, mmPrecision);
    expect(wrapper.vm.envelopeRbs.thetaY).toBeCloseTo(
      0.004370228904778947,
      radPrecision
    );
    expect(wrapper.vm.envelopeRbs.thetaP).toBeCloseTo(
      0.002996816988778066,
      radPrecision
    );

    expect(wrapper.vm.envelopeNonRbs.my).toBeCloseTo(4224203, mmPrecision);
    expect(wrapper.vm.envelopeNonRbs.thetaY).toBeCloseTo(
      0.007301740201213988,
      radPrecision
    );
    expect(wrapper.vm.envelopeNonRbs.thetaP).toBeCloseTo(
      0.00363759535084585,
      radPrecision
    );
  });
});
