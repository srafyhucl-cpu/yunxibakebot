<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import AdminLayout from "@/layouts/AdminLayout.vue";
import AuthLayout from "@/layouts/AuthLayout.vue";

const route = useRoute();

const layoutComponent = computed(() => {
  return route.meta.layout === "auth" ? AuthLayout : AdminLayout;
});
</script>

<template>
  <component :is="layoutComponent">
    <RouterView />
  </component>
</template>
