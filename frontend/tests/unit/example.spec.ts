import ConnectionBrowser from "@/components/ConnectionBrowser.vue";
import { shallowMount } from "@vue/test-utils";
import { expect } from "chai";

describe("ConnectionBrowser.vue", () => {
  it("renders title", () => {
    const title = "Beams";
    const wrapper = shallowMount(ConnectionBrowser);
    expect(wrapper.text()).to.include(title);
  });
});
