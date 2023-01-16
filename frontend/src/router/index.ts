import Vue from "vue";
import VueRouter, { RouteConfig } from "vue-router";

Vue.use(VueRouter);

const routes: Array<RouteConfig> = [
  {
    path: "/",
    name: "Home",
    component: () => import("../views/Home.vue"),
  },
  {
    path: "/connections",
    component: () => import("../views/ConnectionsView.vue"),
    children: [
      {
        path: "",
        redirect: "database",
      },
      {
        path: "database",
        component: () => import("../views/ConnectionsDatabase.vue"),
      },
      {
        path: "fragility-curve",
        component: () => import("../views/ConnectionsFragilityCurve.vue"),
      },
      {
        path: "model",
        component: () => import("../views/ConnectionModelView.vue"),
      },
    ],
  },
  {
    path: "/columns",
    component: () => import("../views/ColumnsView.vue"),
    children: [
      {
        path: "",
        redirect: "database",
      },
      {
        path: "database",
        component: () => import("../views/ColumnsDatabase.vue"),
      },
      {
        path: "fragility-curve",
        component: () => import("../views/ColumnsFragilityCurve.vue"),
      },
      {
        path: "model",
        component: () => import("../views/ColumnsComponentModel.vue"),
      },
    ],
  },
  {
    path: "/braces",
    component: () => import("../views/BracesView.vue"),
    children: [
      {
        path: "",
        redirect: "database",
      },
      {
        path: "database",
        component: () => import("../views/BracesDatabase.vue"),
      },
      {
        path: "fragility-curve",
        component: () => import("../views/BracesFragilityCurve.vue"),
      },
      {
        path: "model",
        component: () => import("../views/BracesModelView.vue"),
      },
    ],
  },
  {
    path: "/materials",
    component: () => import("../views/MaterialsView.vue"),
    children: [
      {
        path: "",
        redirect: "database",
      },
      {
        path: "database",
        component: () => import("../views/MaterialsDatabase.vue"),
      },
      {
        path: "model",
        component: () => import("../views/MaterialsModel.vue"),
      },
    ],
  },
  {
    path: "/about",
    name: "About",
    component: () => import("../views/About.vue"),
  },
];

const router = new VueRouter({
  mode: "history",
  base: process.env.BASE_URL,
  routes,
});

export default router;
