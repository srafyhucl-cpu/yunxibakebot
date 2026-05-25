<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

const props = defineProps<{
  open: boolean;
}>();

const route = useRoute();

const navItems = [
  { label: "概览", to: "/overview", key: "overview" },
  { label: "AI 测试", to: "/chat-test", key: "chat-test" },
  { label: "商品管理", to: "/products", key: "products" },
  { label: "主推款", to: "/products/featured", key: "products-featured" },
  { label: "知识配置", to: "/knowledge", key: "knowledge" },
  { label: "数据观察台", to: "/observability/sessions", key: "observability" },
  { label: "转人工", to: "/transfers", key: "transfers" },
  { label: "系统配置", to: "/settings/shop", key: "settings" },
];

const activeKey = computed(() => route.meta.navKey);
</script>

<template>
  <aside
    class="app-sidebar"
    :class="{ 'app-sidebar--collapsed': !props.open }"
  >
    <div class="app-sidebar__brand">
      <span class="app-sidebar__title">芸熙烘焙</span>
      <span class="app-sidebar__subtitle">新后台 v2</span>
    </div>
    <nav class="app-sidebar__nav">
      <RouterLink
        v-for="item in navItems"
        :key="item.key"
        :to="item.to"
        class="app-sidebar__link"
        :class="{ 'app-sidebar__link--active': activeKey === item.key }"
      >
        {{ item.label }}
      </RouterLink>
    </nav>
  </aside>
</template>
