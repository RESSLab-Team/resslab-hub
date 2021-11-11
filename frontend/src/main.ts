import "./plugins/axios";
import "./registerServiceWorker";

import App from "./App.vue";
import VSwitch from "v-switch-case";
import Vue from "vue";
import router from "./router";
import store from "./store";
import vuetify from "./plugins/vuetify";

Vue.config.productionTip = false;

Vue.use(VSwitch);

new Vue({
  router,
  store,
  vuetify,
  render: (h) => h(App),
}).$mount("#app");
