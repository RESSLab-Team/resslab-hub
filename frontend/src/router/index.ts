import { useUnitStore } from "@/stores/unit";
import Vue from "vue";
import VueRouter, { RouteConfig } from "vue-router";

Vue.use(VueRouter);

const routes: Array<RouteConfig> = [
  {
    path: "/",
    name: "Home",
    component: () => import("../views/HomeView.vue"),
    meta: { showUnitToggle: false },
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
        meta: { showUnitToggle: false },
        component: () => import("../views/ConnectionsDatabase.vue"),
      },
      {
        path: "fragility-curve",
        component: () => import("../views/ConnectionsFragilityCurve.vue"),
      },
      {
        path: "model",
        component: () => import("../views/ConnectionsModelView.vue"),
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
        meta: { showUnitToggle: false },
        component: () => import("../views/ColumnsDatabase.vue"),
      },
      {
        path: "fragility-curve",
        meta: { showUnitToggle: false },
        component: () => import("../views/ColumnsFragilityCurve.vue"),
      },
      {
        path: "model",
        component: () => import("../views/ColumnsModelView.vue"),
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
        meta: { showUnitToggle: false },
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
        meta: { showUnitToggle: false },
        component: () => import("../views/MaterialsDatabase.vue"),
      },
      {
        path: "model",
        component: () => import("../views/MaterialsModelView.vue"),
      },
    ],
  },
];

const router = new VueRouter({
  mode: "history",
  base: process.env.BASE_URL,
  routes,
});

router.afterEach((to) => {
  const unitStore = useUnitStore();
  unitStore.setShowUnitToggle(to.meta?.showUnitToggle ?? true);
});

export default router;
