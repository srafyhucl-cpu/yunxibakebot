<script setup lang="ts">
import { onMounted } from "vue";

import { useOverviewPage } from "./useOverviewPage";

const {
  loading,
  errorMessage,
  productTotal,
  currentContentTotal,
  pendingTransferCount,
  failedHistoryTotal,
  failedWebhookTotal,
  configuredSettingCount,
  recentIssues,
  healthLabel,
  healthType,
  loadOverview,
} = useOverviewPage();

const quickLinks = [
  { title: "AI 测试", desc: "验证回复、意图和工具调用", to: "/chat-test" },
  { title: "商品管理", desc: "检查商品状态和 AI 可读同步", to: "/products" },
  { title: "数据观察台", desc: "追踪内容、回写和 Webhook", to: "/observability/sessions" },
  { title: "系统配置", desc: "巡检渠道和 API 配置状态", to: "/settings/shop" },
];

onMounted(loadOverview);
</script>

<template>
  <section class="overview-page">
    <el-card shadow="never" class="overview-page__hero" v-loading="loading">
      <div>
        <span class="overview-page__eyebrow">Yunxi Admin v2</span>
        <h2>运营概览</h2>
        <p>把当前商品、AI 可读内容、转人工、异常事件和配置健康聚在一个入口，先看有没有火，再决定往哪钻。</p>
      </div>
      <div class="overview-page__health">
        <el-tag :type="healthType" size="large" effect="dark">{{ healthLabel }}</el-tag>
        <el-button type="primary" plain @click="loadOverview">刷新概览</el-button>
      </div>
    </el-card>

    <el-alert
      v-if="errorMessage"
      type="warning"
      show-icon
      :closable="false"
      :title="errorMessage"
    />

    <div class="overview-page__metrics">
      <el-card shadow="never">
        <span>商品总数</span>
        <strong>{{ productTotal }}</strong>
        <router-link to="/products">查看商品</router-link>
      </el-card>
      <el-card shadow="never">
        <span>AI 可读内容</span>
        <strong>{{ currentContentTotal }}</strong>
        <router-link to="/observability/sessions">查看观察台</router-link>
      </el-card>
      <el-card shadow="never">
        <span>待处理转人工</span>
        <strong>{{ pendingTransferCount }}</strong>
        <router-link to="/transfers">处理会话</router-link>
      </el-card>
      <el-card shadow="never">
        <span>配置已就绪项</span>
        <strong>{{ configuredSettingCount }}</strong>
        <router-link to="/settings/shop">巡检配置</router-link>
      </el-card>
    </div>

    <div class="overview-page__grid">
      <el-card shadow="never">
        <template #header>
          <div class="overview-page__section-title">
            <strong>异常入口</strong>
            <router-link to="/observability/failures">全部失败排查</router-link>
          </div>
        </template>
        <div class="overview-page__issues">
          <router-link
            v-for="issue in recentIssues"
            :key="issue.title"
            class="overview-page__issue"
            :to="issue.route"
          >
            <el-tag :type="issue.level" effect="light">{{ issue.level === "success" ? "正常" : "待看" }}</el-tag>
            <div>
              <strong>{{ issue.title }}</strong>
              <span>{{ issue.description }}</span>
            </div>
          </router-link>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <strong>失败快照</strong>
        </template>
        <div class="overview-page__snapshot">
          <div>
            <span>回写失败</span>
            <strong>{{ failedHistoryTotal }}</strong>
            <router-link to="/observability/failures?tab=history">查看回写历史</router-link>
          </div>
          <div>
            <span>Webhook 失败</span>
            <strong>{{ failedWebhookTotal }}</strong>
            <router-link to="/observability/failures?tab=webhooks">查看 Webhook</router-link>
          </div>
        </div>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>
        <strong>快捷入口</strong>
      </template>
      <div class="overview-page__links">
        <router-link
          v-for="link in quickLinks"
          :key="link.to"
          class="overview-page__link"
          :to="link.to"
        >
          <strong>{{ link.title }}</strong>
          <span>{{ link.desc }}</span>
        </router-link>
      </div>
    </el-card>
  </section>
</template>

<style scoped>
.overview-page {
  display: grid;
  gap: 16px;
}

.overview-page__hero {
  background:
    radial-gradient(circle at 12% 20%, rgba(255, 120, 72, 0.18), transparent 28%),
    linear-gradient(135deg, #fff7ee 0%, #ffffff 48%, #eef6ff 100%);
}

.overview-page__hero :deep(.el-card__body) {
  display: flex;
  justify-content: space-between;
  gap: 24px;
}

.overview-page__eyebrow {
  color: var(--yx-accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.overview-page__hero h2 {
  margin: 8px 0;
  font-size: 30px;
}

.overview-page__hero p,
.overview-page__metrics span,
.overview-page__issue span,
.overview-page__link span,
.overview-page__snapshot span {
  color: var(--yx-text-muted);
}

.overview-page__health {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.overview-page__metrics,
.overview-page__grid,
.overview-page__links,
.overview-page__snapshot {
  display: grid;
  gap: 16px;
}

.overview-page__metrics {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.overview-page__metrics :deep(.el-card__body),
.overview-page__snapshot > div {
  display: grid;
  gap: 8px;
}

.overview-page__metrics strong,
.overview-page__snapshot strong {
  font-size: 28px;
}

.overview-page__metrics a,
.overview-page__section-title a,
.overview-page__snapshot a {
  color: var(--yx-accent);
  text-decoration: none;
}

.overview-page__grid {
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.6fr);
}

.overview-page__section-title {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.overview-page__issues,
.overview-page__links {
  display: grid;
  gap: 12px;
}

.overview-page__issue,
.overview-page__link {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  border: 1px solid var(--yx-border);
  border-radius: 14px;
  padding: 14px;
  color: inherit;
  text-decoration: none;
}

.overview-page__issue div,
.overview-page__link {
  display: grid;
  gap: 4px;
}

.overview-page__links {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.overview-page__snapshot {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 1100px) {
  .overview-page__metrics,
  .overview-page__links {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .overview-page__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 720px) {
  .overview-page__hero :deep(.el-card__body),
  .overview-page__health {
    flex-direction: column;
  }

  .overview-page__metrics,
  .overview-page__links,
  .overview-page__snapshot {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
