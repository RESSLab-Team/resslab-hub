import router from "@/router";
import Vue from "vue";
import VueGtag from "vue-gtag";

Vue.use(
  VueGtag,
  {
    config: { id: "G-HDDWMBZ6XJ", params: { anonymize_ip: true } },
  },
  router
);
