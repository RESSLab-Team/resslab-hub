import SpecimenBrowser from "@/components/SpecimenBrowser.vue";
import { expect } from "chai";
import { shallowMount } from "@vue/test-utils";

describe("SpecimenBrowser.vue", () => {
  it("renders title", () => {
    const title = "Beams";
    const wrapper = shallowMount(SpecimenBrowser);
    expect(wrapper.text()).to.include(title);
  });
});
