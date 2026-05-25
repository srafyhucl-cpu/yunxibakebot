<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import { useAppStore } from "@/stores/app";
import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const appStore = useAppStore();
const authStore = useAuthStore();

const title = computed(() => String(route.meta.title || "芸熙烘焙后台"));
</script>

<template>
  <header class="topbar">
    <div class="topbar__left">
      <el-button
        text
        class="topbar__menu-btn"
        @click="appStore.toggleSidebar"
      >
        菜单
      </el-button>
      <div>
        <div class="topbar__title">{{ title }}</div>
        <div class="topbar__subtitle">后台前端重构阶段 A</div>
      </div>
    </div>
    <div class="topbar__right">
      <span class="topbar__user">
        {{ authStore.profile?.name || "管理员" }}
      </span>
    </div>
  </header>
</template>
