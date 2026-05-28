import type { RouteRecordRaw } from "vue-router";

export const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: () => import("@/pages/login/LoginPage.vue"),
    meta: {
      layout: "auth",
      title: "登录",
    },
  },
  {
    path: "/",
    redirect: "/overview",
  },
  {
    path: "/overview",
    name: "overview",
    component: () => import("@/pages/overview/OverviewPage.vue"),
    meta: {
      title: "概览",
      navKey: "overview",
    },
  },
  {
    path: "/ai-dialog",
    name: "ai-dialog",
    component: () => import("@/pages/ai-dialog/AiDialogPage.vue"),
    meta: {
      title: "AI 对话",
      navKey: "ai-dialog",
    },
  },
  {
    path: "/products",
    name: "products",
    component: () => import("@/pages/products/ProductsPage.vue"),
    meta: {
      title: "商品管理",
      navKey: "products",
    },
  },
  {
    path: "/products/featured",
    name: "products-featured",
    component: () => import("@/pages/products/FeaturedProductsPage.vue"),
    meta: {
      title: "主推款",
      navKey: "products-featured",
    },
  },
  {
    path: "/knowledge",
    name: "knowledge",
    component: () => import("@/pages/knowledge/KnowledgePage.vue"),
    meta: {
      title: "知识配置",
      navKey: "knowledge",
    },
  },
  {
    path: "/observability",
    redirect: "/observability/sessions",
  },
  {
    path: "/observability/sessions",
    name: "observability-sessions",
    component: () => import("@/pages/observability/ObservabilitySessionsPage.vue"),
    meta: {
      title: "数据观察台",
      navKey: "observability",
    },
  },
  {
    path: "/observability/failures",
    name: "observability-failures",
    component: () => import("@/pages/observability/ObservabilityFailuresPage.vue"),
    meta: {
      title: "失败排查",
      navKey: "observability",
    },
  },
  {
    path: "/transfers",
    name: "transfers",
    component: () => import("@/pages/transfers/TransfersPage.vue"),
    meta: {
      title: "转人工",
      navKey: "transfers",
    },
  },
  {
    path: "/settings",
    redirect: "/settings/shop",
  },
  {
    path: "/settings/shop",
    name: "settings-shop",
    component: () => import("@/pages/settings/ShopSettingsPage.vue"),
    meta: {
      title: "店铺配置",
      navKey: "settings",
    },
  },
  {
    path: "/settings/channel",
    name: "settings-channel",
    component: () => import("@/pages/settings/ChannelSettingsPage.vue"),
    meta: {
      title: "渠道配置",
      navKey: "settings",
    },
  },
  {
    path: "/settings/api",
    name: "settings-api",
    component: () => import("@/pages/settings/ApiSettingsPage.vue"),
    meta: {
      title: "API 配置",
      navKey: "settings",
    },
  },
];
