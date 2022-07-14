import ConnectionComponent from "@/components/connections/ConnectionComponent.vue";
import { shallowMount } from "@vue/test-utils";
import { expect } from "chai";

describe("ConnectionComponent.vue", () => {
  it("aisc - W36X150", () => {
    const wrapper = shallowMount<ConnectionComponent>(ConnectionComponent);
    wrapper.setData({
      section: {
        id: "W36X150",
        bf: 304.8,
        h: 826.0079999999999,
        tf: 23.875999999999998,
        tw: 15.875,
        ix: 3762732087.4239993,
        zx: 9520884.183999998,
        ry: 62.738,
        d: 911.8599999999999,
      },
    });

    expect(wrapper.vm.backboneRbs.k).to.be.closeTo(578520058, 1, "k");
    expect(wrapper.vm.backboneRbs.my).to.be.closeTo(2528354, 1, "my");
    expect(wrapper.vm.backboneRbs.thetaY).to.be.closeTo(
      0.0043,
      0.0001,
      "thetaY"
    );
  });
});
