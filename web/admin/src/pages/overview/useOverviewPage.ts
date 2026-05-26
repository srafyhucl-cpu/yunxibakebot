import { computed, ref } from "vue";

import { observabilityService } from "@/services/observability";
import { productsService } from "@/services/products";
import { settingsService } from "@/services/settings";
import { transfersService } from "@/services/transfers";

interface OverviewRecentIssue {
  title: string;
  description: string;
  route: string;
  level: "success" | "warning" | "danger" | "info";
}

const FIRST_PAGE = 1;

export function useOverviewPage() {
  const loading = ref(false);
  const errorMessage = ref("");
  const productTotal = ref(0);
  const currentContentTotal = ref(0);
  const pendingTransferCount = ref(0);
  const failedHistoryTotal = ref(0);
  const failedWebhookTotal = ref(0);
  const configuredSettingCount = ref(0);
  const recentIssues = ref<OverviewRecentIssue[]>([]);

  const hasFailures = computed(() => failedHistoryTotal.value + failedWebhookTotal.value > 0);
  const healthLabel = computed(() => {
    if (errorMessage.value) {
      return "需要检查";
    }
    if (hasFailures.value || pendingTransferCount.value > 0) {
      return "有待处理";
    }
    return "运行平稳";
  });

  const healthType = computed<"success" | "warning" | "danger">(() => {
    if (errorMessage.value) {
      return "danger";
    }
    return hasFailures.value || pendingTransferCount.value > 0 ? "warning" : "success";
  });

  async function loadOverview() {
    loading.value = true;
    errorMessage.value = "";

    const [products, currentContent, transfers, failedHistory, failedWebhooks, settings] =
      await Promise.allSettled([
        productsService.listProducts(FIRST_PAGE, ""),
        observabilityService.listCurrent({
          page: FIRST_PAGE,
          view: "knowledge",
          category: "",
          keyword: "",
          productStatus: "",
        }),
        transfersService.listPendingTransfers(),
        observabilityService.listHistory({
          page: FIRST_PAGE,
          source: "",
          status: "failed",
          entityType: "",
          keyword: "",
        }),
        observabilityService.listWebhooks({
          page: FIRST_PAGE,
          status: "failed",
          eventType: "",
          keyword: "",
        }),
        settingsService.getSummary(),
      ]);

    if (products.status === "fulfilled") {
      productTotal.value = products.value.total;
    }
    if (currentContent.status === "fulfilled") {
      currentContentTotal.value = currentContent.value.total;
    }
    if (transfers.status === "fulfilled") {
      pendingTransferCount.value = transfers.value.length;
    }
    if (failedHistory.status === "fulfilled") {
      failedHistoryTotal.value = failedHistory.value.total;
    }
    if (failedWebhooks.status === "fulfilled") {
      failedWebhookTotal.value = failedWebhooks.value.total;
    }
    if (settings.status === "fulfilled") {
      configuredSettingCount.value = [
        settings.value.api.adminTokenConfigured,
        settings.value.api.deepseekApiKeyConfigured,
        settings.value.channels.youzan.clientIdConfigured,
        settings.value.channels.youzan.clientSecretConfigured,
        settings.value.channels.youzan.kdtIdConfigured,
        settings.value.channels.youzan.webhookTokenConfigured,
      ].filter(Boolean).length;
    }

    recentIssues.value = buildRecentIssues();
    const failedRequests = [products, currentContent, transfers, failedHistory, failedWebhooks, settings]
      .filter((item) => item.status === "rejected").length;
    if (failedRequests > 0) {
      errorMessage.value = `${failedRequests} 个概览指标加载失败，请刷新重试`;
    }
    loading.value = false;
  }

  function buildRecentIssues(): OverviewRecentIssue[] {
    const issues: OverviewRecentIssue[] = [];
    if (pendingTransferCount.value > 0) {
      issues.push({
        title: "有待处理转人工",
        description: `${pendingTransferCount.value} 个会话正在等待接单或处理`,
        route: "/transfers",
        level: "warning",
      });
    }
    if (failedHistoryTotal.value > 0) {
      issues.push({
        title: "回写历史存在失败",
        description: `${failedHistoryTotal.value} 条内容回写需要排查`,
        route: "/observability/failures?tab=history",
        level: "danger",
      });
    }
    if (failedWebhookTotal.value > 0) {
      issues.push({
        title: "Webhook 存在失败",
        description: `${failedWebhookTotal.value} 条 Webhook 事件需要追踪`,
        route: "/observability/failures?tab=webhooks",
        level: "danger",
      });
    }
    if (!issues.length) {
      issues.push({
        title: "暂无高优先级异常",
        description: "可以继续检查商品、知识配置和系统配置状态",
        route: "/observability/sessions",
        level: "success",
      });
    }
    return issues;
  }

  return {
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
  };
}
