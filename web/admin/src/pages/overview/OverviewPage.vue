<script setup lang="ts">
import { onMounted } from "vue";
import {
  ChatDotRound,
  CircleCheckFilled,
  Clock,
  Document,
  Goods,
  Histogram,
  RefreshRight,
  Service,
  Setting,
  WarningFilled,
} from "@element-plus/icons-vue";

import { useOverviewPage } from "./useOverviewPage";

const {
  loading,
  errorMessage,
  lastRefreshedAt,
  productTotal,
  currentContentTotal,
  pendingTransferCount,
  failedHistoryTotal,
  failedWebhookTotal,
  slowWebhookTotal,
  processingWebhookTotal,
  configuredSettingCount,
  recentIssues,
  healthLabel,
  healthType,
  loadOverview,
} = useOverviewPage();

const quickLinks = [
  { title: "AI 对话", desc: "验证回复、意图和工具调用", to: "/ai-dialog", icon: ChatDotRound },
  { title: "商品管理", desc: "检查商品和 AI 可读同步", to: "/products", icon: Goods },
  { title: "数据观察台", desc: "追踪内容、回写和 Webhook", to: "/observability/sessions", icon: Histogram },
  { title: "系统配置", desc: "巡检渠道和 API 配置状态", to: "/settings/shop", icon: Setting },
];

onMounted(loadOverview);
</script>

<template>
  <section class="overview-page">
    <!-- Hero -->
    <el-card shadow="never" class="overview-page__hero" v-loading="loading">
      <div class="hero-left">
        <span class="hero-eyebrow">Yunxi Admin v2</span>
        <h2>运营概览</h2>
        <p>商品 · AI 内容 · 转人工 · 异常事件一屏掌握</p>
      </div>
      <div class="hero-right">
        <el-tag :type="healthType" size="large" effect="dark" class="health-tag">
          <span class="health-dot" :class="`health-dot--${healthType}`" />
          {{ healthLabel }}
        </el-tag>
        <div class="hero-refresh">
          <el-button :icon="RefreshRight" plain size="small" @click="loadOverview">刷新</el-button>
          <span v-if="lastRefreshedAt" class="refresh-time">
            <el-icon size="11"><Clock /></el-icon>
            {{ lastRefreshedAt }}
          </span>
        </div>
      </div>
    </el-card>

    <!-- 加载失败提示 -->
    <el-alert v-if="errorMessage" type="warning" show-icon :closable="false" :title="errorMessage" />

    <!-- 指标卡 -->
    <div class="metrics-grid">
      <router-link to="/products" class="metric-card metric-card--blue">
        <div class="metric-card__header">
          <span class="metric-card__label">商品总数</span>
          <span class="metric-icon metric-icon--blue"><el-icon size="18"><Goods /></el-icon></span>
        </div>
        <strong class="metric-card__value">{{ productTotal }}</strong>
        <span class="metric-card__cta">查看商品 →</span>
      </router-link>

      <router-link to="/observability/sessions" class="metric-card metric-card--green">
        <div class="metric-card__header">
          <span class="metric-card__label">AI 可读内容</span>
          <span class="metric-icon metric-icon--green"><el-icon size="18"><Document /></el-icon></span>
        </div>
        <strong class="metric-card__value">{{ currentContentTotal }}</strong>
        <span class="metric-card__cta">查看观察台 →</span>
      </router-link>

      <router-link
        to="/transfers"
        class="metric-card"
        :class="pendingTransferCount > 0 ? 'metric-card--orange' : 'metric-card--neutral'"
      >
        <div class="metric-card__header">
          <span class="metric-card__label">待处理转人工</span>
          <span
            class="metric-icon"
            :class="pendingTransferCount > 0 ? 'metric-icon--orange' : 'metric-icon--neutral'"
          >
            <el-icon size="18"><Service /></el-icon>
          </span>
        </div>
        <strong class="metric-card__value" :class="{ 'is-orange': pendingTransferCount > 0 }">
          {{ pendingTransferCount }}
        </strong>
        <span class="metric-card__cta">处理会话 →</span>
      </router-link>

      <router-link to="/settings/shop" class="metric-card metric-card--purple">
        <div class="metric-card__header">
          <span class="metric-card__label">配置已就绪</span>
          <span class="metric-icon metric-icon--purple"><el-icon size="18"><Setting /></el-icon></span>
        </div>
        <strong class="metric-card__value">
          {{ configuredSettingCount }}<small>/6</small>
        </strong>
        <span class="metric-card__cta">巡检配置 →</span>
      </router-link>
    </div>

    <!-- 异常入口 + 失败快照 -->
    <div class="overview-grid">
      <el-card shadow="never">
        <template #header>
          <div class="section-title">
            <strong>异常入口</strong>
            <router-link to="/observability/failures">全部失败排查 →</router-link>
          </div>
        </template>
        <div class="issues-list">
          <router-link
            v-for="issue in recentIssues"
            :key="issue.title"
            class="issue-item"
            :class="`issue-item--${issue.level}`"
            :to="issue.route"
          >
            <el-icon class="issue-item__icon" size="20">
              <CircleCheckFilled v-if="issue.level === 'success'" />
              <WarningFilled v-else />
            </el-icon>
            <div class="issue-item__body">
              <strong>{{ issue.title }}</strong>
              <span>{{ issue.description }}</span>
            </div>
          </router-link>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="section-title">
            <strong>失败快照</strong>
            <el-tag
              v-if="failedHistoryTotal + failedWebhookTotal + slowWebhookTotal > 0"
              type="danger"
              size="small"
              effect="dark"
              round
            >
              {{ failedHistoryTotal + failedWebhookTotal + slowWebhookTotal }} 条待排查
            </el-tag>
          </div>
        </template>
        <div class="snapshot-grid">
          <div class="snapshot-item">
            <span>回写失败</span>
            <div class="snapshot-count">
              <el-icon v-if="failedHistoryTotal > 0" size="16" class="snapshot-warn-icon"><WarningFilled /></el-icon>
              <strong :class="{ 'is-danger': failedHistoryTotal > 0 }">{{ failedHistoryTotal }}</strong>
            </div>
            <router-link
              class="snapshot-action"
              :class="{ 'snapshot-action--danger': failedHistoryTotal > 0 }"
              to="/observability/failures?tab=history"
            >立即排查 →</router-link>
          </div>
          <div class="snapshot-item">
            <span>Webhook 失败</span>
            <div class="snapshot-count">
              <el-icon v-if="failedWebhookTotal > 0" size="16" class="snapshot-warn-icon"><WarningFilled /></el-icon>
              <strong :class="{ 'is-danger': failedWebhookTotal > 0 }">{{ failedWebhookTotal }}</strong>
            </div>
            <router-link
              class="snapshot-action"
              :class="{ 'snapshot-action--danger': failedWebhookTotal > 0 }"
              to="/observability/failures?tab=webhooks"
            >立即排查 →</router-link>
          </div>
          <div class="snapshot-item">
            <span>慢 Webhook</span>
            <div class="snapshot-count">
              <el-icon v-if="slowWebhookTotal > 0" size="16" class="snapshot-warn-icon"><WarningFilled /></el-icon>
              <strong :class="{ 'is-danger': slowWebhookTotal > 0 }">{{ slowWebhookTotal }}</strong>
            </div>
            <router-link
              class="snapshot-action"
              :class="{ 'snapshot-action--danger': slowWebhookTotal > 0 }"
              to="/observability/sessions?tab=webhooks"
            >查看耗时 →</router-link>
          </div>
          <div class="snapshot-item">
            <span>Webhook 处理中</span>
            <div class="snapshot-count">
              <strong>{{ processingWebhookTotal }}</strong>
            </div>
            <router-link
              class="snapshot-action"
              to="/observability/sessions?tab=webhooks&webhookStatus=processing"
            >查看队列 →</router-link>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 快捷入口 -->
    <el-card shadow="never">
      <template #header><strong>快捷入口</strong></template>
      <div class="quick-links">
        <router-link v-for="link in quickLinks" :key="link.to" class="quick-link" :to="link.to">
          <span class="quick-link__icon">
            <el-icon size="20"><component :is="link.icon" /></el-icon>
          </span>
          <div class="quick-link__body">
            <strong>{{ link.title }}</strong>
            <span>{{ link.desc }}</span>
          </div>
        </router-link>
      </div>
    </el-card>
  </section>
</template>

<style scoped>
/* ── 整体布局 ─────────────────────────────────── */
.overview-page {
  display: grid;
  gap: 16px;
}

/* ── Hero ────────────────────────────────────── */
.overview-page__hero {
  background:
    radial-gradient(circle at 12% 20%, rgba(255, 120, 72, 0.18), transparent 28%),
    linear-gradient(135deg, #fff7ee 0%, #ffffff 48%, #eef6ff 100%);
}

.overview-page__hero :deep(.el-card__body) {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
}

.hero-eyebrow {
  color: var(--yx-brand);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.hero-left h2 {
  margin: 6px 0 4px;
  font-size: 28px;
}

.hero-left p {
  margin: 0;
  font-size: 14px;
  color: var(--yx-text-muted);
}

.hero-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
  flex-shrink: 0;
}

.health-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.health-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.9;
  animation: blink 2.4s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 0.9; }
  50% { opacity: 0.3; }
}

.hero-refresh {
  display: flex;
  align-items: center;
  gap: 8px;
}

.refresh-time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--yx-text-muted);
}

/* ── 指标卡 ──────────────────────────────────── */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.metric-card {
  position: relative;
  display: grid;
  gap: 6px;
  padding: 20px;
  background: #fff;
  border: 1px solid var(--yx-border);
  border-radius: 14px;
  text-decoration: none;
  color: var(--yx-text);
  overflow: hidden;
  transition: box-shadow 0.2s, transform 0.2s;
}

.metric-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  border-radius: 14px 14px 0 0;
}

.metric-card--blue::before   { background: #3b82f6; }
.metric-card--green::before  { background: #10b981; }
.metric-card--orange::before { background: #f59e0b; }
.metric-card--purple::before { background: #8b5cf6; }
.metric-card--neutral::before { background: var(--yx-border); }

.metric-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.metric-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-card__label {
  font-size: 13px;
  color: var(--yx-text-muted);
}

.metric-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.metric-icon--blue   { background: #eff6ff; color: #3b82f6; }
.metric-icon--green  { background: #ecfdf5; color: #10b981; }
.metric-icon--orange { background: #fff7ed; color: #f59e0b; }
.metric-icon--purple { background: #f5f3ff; color: #8b5cf6; }
.metric-icon--neutral { background: var(--yx-bg); color: var(--yx-text-muted); }

.metric-card__value {
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
  margin: 6px 0 2px;
}

.metric-card__value.is-orange { color: #f59e0b; }

.metric-card__value small {
  font-size: 15px;
  font-weight: 500;
  color: var(--yx-text-muted);
  margin-left: 2px;
}

.metric-card__cta {
  font-size: 12px;
  color: var(--yx-brand);
}

/* ── 异常入口 + 失败快照 ──────────────────────── */
.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.6fr);
  gap: 16px;
}

.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title a {
  font-size: 13px;
  color: var(--yx-brand);
  text-decoration: none;
}

.issues-list {
  display: grid;
  gap: 10px;
}

.issue-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--yx-border);
  border-left-width: 4px;
  border-radius: 10px;
  text-decoration: none;
  color: var(--yx-text);
  transition: background 0.15s;
}

.issue-item:hover { background: var(--yx-bg); }

.issue-item--success { border-left-color: #10b981; }
.issue-item--warning { border-left-color: #f59e0b; }
.issue-item--danger  { border-left-color: #ef4444; }
.issue-item--info    { border-left-color: var(--yx-border); }

.issue-item__icon { flex-shrink: 0; margin-top: 1px; }
.issue-item--success .issue-item__icon { color: #10b981; }
.issue-item--warning .issue-item__icon { color: #f59e0b; }
.issue-item--danger  .issue-item__icon { color: #ef4444; }

.issue-item__body { display: grid; gap: 3px; }
.issue-item__body span { font-size: 13px; color: var(--yx-text-muted); }

.snapshot-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.snapshot-item { display: grid; gap: 6px; }
.snapshot-item span { font-size: 13px; color: var(--yx-text-muted); }

.snapshot-count {
  display: flex;
  align-items: center;
  gap: 6px;
}

.snapshot-warn-icon { color: #ef4444; flex-shrink: 0; }

.snapshot-count strong { font-size: 28px; font-weight: 700; }
.snapshot-count strong.is-danger { color: #ef4444; }

.snapshot-action {
  display: inline-block;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--yx-border);
  background: var(--yx-bg);
  color: var(--yx-text-muted);
  text-decoration: none;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.snapshot-action--danger {
  color: #ef4444;
  border-color: #fecaca;
  background: #fff5f5;
}

.snapshot-action--danger:hover { background: #fee2e2; }

/* ── 快捷入口 ────────────────────────────────── */
.quick-links {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.quick-link {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--yx-border);
  border-radius: 12px;
  text-decoration: none;
  color: var(--yx-text);
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
}

.quick-link:hover {
  background: var(--yx-brand-soft);
  border-color: var(--yx-brand);
  box-shadow: 0 4px 12px rgba(236, 111, 94, 0.12);
}

.quick-link__icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--yx-brand-soft);
  color: var(--yx-brand);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s;
}

.quick-link:hover .quick-link__icon { background: rgba(236, 111, 94, 0.2); }

.quick-link__body { display: grid; gap: 2px; }
.quick-link__body span { font-size: 12px; color: var(--yx-text-muted); }

/* ── 响应式 ──────────────────────────────────── */
@media (max-width: 1100px) {
  .metrics-grid,
  .quick-links {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .overview-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 720px) {
  .overview-page__hero :deep(.el-card__body) {
    flex-direction: column;
  }

  .hero-right { align-items: flex-start; }

  .metrics-grid,
  .quick-links,
  .snapshot-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
