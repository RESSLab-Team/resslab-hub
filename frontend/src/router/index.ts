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
    component: () => import("../views/Connections.vue"),
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
        component: () => import("../views/ConnectionsComponentModel.vue"),
      },
    ],
  },
  {
    path: "/columns",
    component: () => import("../views/Columns.vue"),
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
    component: () => import("../views/Braces.vue"),
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
        component: () => import("../views/BracesComponentModel.vue"),
      },
    ],
  },
  {
    path: "/materials",
    component: () => import("../views/Materials.vue"),
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
