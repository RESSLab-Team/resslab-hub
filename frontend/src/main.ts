import VSwitch from "v-switch-case";
import Vue from "vue";
import App from "./App.vue";
import i18n from "./i18n";
import "./plugins/axios";
import vuetify from "./plugins/vuetify";
import "./registerServiceWorker";
import router from "./router";
import store from "./store";
import "./styles/main.scss";

Vue.config.productionTip = false;

Vue.use(VSwitch);

Vue.filter(
  "formatNumber",
  function (value: number | null, fractionDigits: number | undefined): string {
    if (value === null) {
      return "Not Applicable";
    } else if (isNaN(value)) {
      return "Not Reported";
    } else {
      return value.toFixed(fractionDigits);
    }
  }
);
Vue.filter("formatString", function (value: string | null): string {
  if (value === null) {
    return "Not Applicable";
  } else if (value === "NR") {
    return "Not Reported";
  } else {
    return value;
  }
});

new Vue({
  router,
  store,
  vuetify,
  i18n,
  render: (h) => h(App),
}).$mount("#app");
