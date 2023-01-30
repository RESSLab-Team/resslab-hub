import { formatNumber, formatString } from "@/utils/formatter";
import VSwitch from "v-switch-case";
import Vue from "vue";
import App from "./App.vue";
import i18n from "./i18n";
import "./plugins/axios";
import "./plugins/gtag";
import vuetify from "./plugins/vuetify";
import "./registerServiceWorker";
import router from "./router";
import store from "./store";
import "./styles/main.scss";

Vue.config.productionTip = false;

Vue.use(VSwitch);

Vue.filter("formatNumber", formatNumber);
Vue.filter("formatString", formatString);

new Vue({
  router,
  store,
  vuetify,
  i18n,
  render: (h) => h(App),
}).$mount("#app");
