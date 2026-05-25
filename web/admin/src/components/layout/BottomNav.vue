<script setup lang="ts">
import { useRoute } from "vue-router";

const route = useRoute();

const navItems = [
  { label: "概览", to: "/overview", key: "overview" },
  { label: "AI 测试", to: "/chat-test", key: "chat-test" },
  { label: "商品", to: "/products", key: "products" },
  { label: "观察台", to: "/observability/sessions", key: "observability" },
  { label: "更多", to: "/settings/shop", key: "settings" },
];
</script>

<template>
  <nav class="bottom-nav">
    <RouterLink
      v-for="item in navItems"
      :key="item.key"
      :to="item.to"
      class="bottom-nav__item"
      :class="{ 'bottom-nav__item--active': route.meta.navKey === item.key }"
    >
      {{ item.label }}
    </RouterLink>
  </nav>
</template>
