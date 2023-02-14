import { formatNumber, formatString } from "@/utils/formatter";
import { createPinia, PiniaVuePlugin } from "pinia";
import VSwitch from "v-switch-case";
import Vue from "vue";
import App from "./App.vue";
import i18n from "./i18n";
import "./plugins/axios";
import "./plugins/gtag";
import vuetify from "./plugins/vuetify";
import "./registerServiceWorker";
import router from "./router";
import "./styles/main.scss";

Vue.use(PiniaVuePlugin);
const pinia = createPinia();

Vue.config.productionTip = false;

Vue.use(VSwitch);

Vue.filter("formatNumber", formatNumber);
Vue.filter("formatString", formatString);

new Vue({
  router,
  vuetify,
  i18n,
  pinia,
  render: (h) => h(App),
}).$mount("#app");
