<script setup lang="ts">
import { Search } from "@element-plus/icons-vue";
import { reactive } from "vue";

import ObservabilityDetailDrawer from "./ObservabilityDetailDrawer.vue";
import { useObservabilityWorkbench } from "./useObservabilityWorkbench";

import type { ObservabilityTab } from "@/types/observability";

const props = defineProps<{
  mode: "workspace" | "failures";
}>();

const page = reactive(useObservabilityWorkbench(props.mode));

const workspaceTabs: Array<{ key: ObservabilityTab; label: string }> = [
  { key: "current", label: "当前内容" },
  { key: "history", label: "回写历史" },
  { key: "webhooks", label: "Webhook 审计" },
];

const failureTabs: Array<{ key: ObservabilityTab; label: string }> = [
  { key: "history", label: "失败回写" },
  { key: "webhooks", label: "失败 Webhook" },
];

function updateDrawerVisible(value: boolean) {
  if (!value) {
    page.closeDrawer();
  }
}
</script>

<template>
  <section class="observability-page">
    <div class="observability-page__summary">
      <el-card shadow="never">
        <div class="observability-page__metric">
          <span class="observability-page__metric-label">{{ page.summaryLabel }}</span>
          <strong class="observability-page__metric-value">{{ page.total }}</strong>
        </div>
      </el-card>
      <el-card shadow="never">
        <div class="observability-page__metric">
          <span class="observability-page__metric-label">当前页记录</span>
          <strong class="observability-page__metric-value">{{ page.listCount }}</strong>
        </div>
      </el-card>
      <el-card shadow="never">
        <div class="observability-page__metric">
          <span class="observability-page__metric-label">当前页异常</span>
          <strong class="observability-page__metric-value">{{ page.issueCount }}</strong>
        </div>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="observability-page__header">
          <div>
            <strong>{{ props.mode === "workspace" ? "数据观察台" : "失败排查" }}</strong>
            <p>
              {{
                props.mode === "workspace"
                  ? "先把当前内容、回写历史和 Webhook 审计都接通，优先满足查问题和追溯来源。"
                  : "聚焦失败记录，优先判断失败发生在哪个环节、携带了什么上下文。"
              }}
            </p>
          </div>
          <div class="observability-page__tabs">
            <el-button
              v-for="tab in props.mode === 'workspace' ? workspaceTabs : failureTabs"
              :key="tab.key"
              :type="page.activeTab === tab.key ? 'primary' : 'default'"
              plain
              @click="page.switchTab(tab.key)"
            >
              {{ tab.label }}
            </el-button>
          </div>
        </div>
      </template>

      <el-form
        v-if="page.activeTab === 'current'"
        class="observability-page__filters"
        @submit.prevent="page.submitCurrentFilters"
      >
        <el-select v-model="page.currentViewDraft" placeholder="内容范围">
          <el-option label="知识内容" value="knowledge" />
          <el-option label="商品内容" value="products" />
        </el-select>
        <el-select
          v-if="page.currentViewDraft === 'knowledge'"
          v-model="page.currentCategoryDraft"
          clearable
          placeholder="知识分类"
        >
          <el-option label="全部分类" value="" />
          <el-option label="FAQ" value="faq" />
          <el-option label="规则" value="rule" />
          <el-option label="话术" value="copywriting" />
          <el-option label="商品知识" value="product" />
        </el-select>
        <el-select
          v-else
          v-model="page.currentProductStatusDraft"
          clearable
          placeholder="商品状态"
        >
          <el-option label="全部状态" value="" />
          <el-option label="在售" value="1" />
          <el-option label="下架" value="0" />
        </el-select>
        <el-input
          v-model="page.currentKeywordDraft"
          clearable
          placeholder="搜索标题、关键词或商品别名"
          @keyup.enter="page.submitCurrentFilters"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="page.submitCurrentFilters">筛选</el-button>
      </el-form>

      <el-form
        v-else-if="page.activeTab === 'history'"
        class="observability-page__filters"
        @submit.prevent="page.submitHistoryFilters"
      >
        <el-select v-model="page.historyStatusDraft" clearable placeholder="处理结果">
          <el-option label="全部结果" value="" />
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-select v-model="page.historySourceDraft" clearable placeholder="来源">
          <el-option label="全部来源" value="" />
          <el-option label="后台知识配置" value="admin_knowledge" />
          <el-option label="有赞 Webhook" value="youzan_webhook" />
          <el-option label="种子导入" value="seed_knowledge" />
        </el-select>
        <el-select v-model="page.historyEntityTypeDraft" clearable placeholder="实体类型">
          <el-option label="全部类型" value="" />
          <el-option label="知识" value="knowledge" />
          <el-option label="商品" value="product" />
        </el-select>
        <el-input
          v-model="page.historyKeywordDraft"
          clearable
          placeholder="搜索标题、实体键或来源引用"
          @keyup.enter="page.submitHistoryFilters"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="page.submitHistoryFilters">筛选</el-button>
      </el-form>

      <el-form
        v-else
        class="observability-page__filters"
        @submit.prevent="page.submitWebhookFilters"
      >
        <el-select v-model="page.webhookStatusDraft" clearable placeholder="处理结果">
          <el-option label="全部结果" value="" />
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
          <el-option label="处理中" value="processing" />
        </el-select>
        <el-input
          v-model="page.webhookEventTypeDraft"
          clearable
          placeholder="事件类型，如 ITEM_INFO"
          @keyup.enter="page.submitWebhookFilters"
        />
        <el-input
          v-model="page.webhookKeywordDraft"
          clearable
          placeholder="搜索 msg_id、业务键或错误信息"
          @keyup.enter="page.submitWebhookFilters"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="page.submitWebhookFilters">筛选</el-button>
      </el-form>

      <el-alert
        v-if="page.errorMessage"
        class="observability-page__error"
        type="error"
        show-icon
        :closable="false"
      >
        <template #title>
          <span>{{ page.errorMessage }}</span>
          <el-button link type="primary" @click="page.retryLoadData">重试</el-button>
        </template>
      </el-alert>

      <div class="observability-page__desktop">
        <el-table
          v-if="page.activeTab === 'current'"
          :data="page.currentRows"
          v-loading="page.loading"
          stripe
        >
          <el-table-column prop="title" label="内容" min-width="240">
            <template #default="{ row }">
              <button class="observability-page__title-button" type="button" @click="page.openCurrentDetail(row)">
                <strong>{{ row.title }}</strong>
                <span>{{ row.subtitle || `${row.category} · ${row.entityKey}` }}</span>
              </button>
            </template>
          </el-table-column>
          <el-table-column prop="statusText" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.statusType" effect="light">{{ row.statusText || "未标记" }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="syncSourceLabel" label="最后来源" min-width="150" />
          <el-table-column prop="updatedAtLabel" label="更新时间" min-width="170" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="page.openCurrentDetail(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-table
          v-else-if="page.activeTab === 'history'"
          :data="page.historyRows"
          v-loading="page.loading"
          stripe
        >
          <el-table-column prop="title" label="回写对象" min-width="220">
            <template #default="{ row }">
              <button class="observability-page__title-button" type="button" @click="page.openHistoryDetail(row)">
                <strong>{{ row.title }}</strong>
                <span>{{ row.entityType }} · {{ row.entityKey }}</span>
              </button>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="结果" width="120">
            <template #default="{ row }">
              <el-tag :type="row.statusType" effect="light">{{ row.status || "未标记" }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source" label="来源" min-width="140" />
          <el-table-column prop="action" label="动作" min-width="120" />
          <el-table-column prop="errorLabel" label="错误信息" min-width="220" show-overflow-tooltip />
          <el-table-column prop="occurredAtLabel" label="发生时间" min-width="170" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="page.openHistoryDetail(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-table v-else :data="page.webhookRows" v-loading="page.loading" stripe>
          <el-table-column prop="eventType" label="事件" min-width="180">
            <template #default="{ row }">
              <button class="observability-page__title-button" type="button" @click="page.openWebhookDetail(row)">
                <strong>{{ row.eventType || "未记录事件" }}</strong>
                <span>{{ row.businessType }} · {{ row.businessKey || row.msgId || "-" }}</span>
              </button>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="结果" width="120">
            <template #default="{ row }">
              <el-tag :type="row.statusType" effect="light">{{ row.status || "未标记" }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="processStage" label="处理阶段" min-width="140" />
          <el-table-column prop="durationLabel" label="耗时" min-width="100" />
          <el-table-column prop="errorLabel" label="错误信息" min-width="220" show-overflow-tooltip />
          <el-table-column prop="receivedAtLabel" label="接收时间" min-width="170" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="page.openWebhookDetail(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="observability-page__mobile">
        <el-skeleton :rows="4" animated v-if="page.loading" />

        <div v-else-if="page.activeTab === 'current'" class="observability-page__cards">
          <button
            v-for="row in page.currentRows"
            :key="`${row.entityType}-${row.entityKey}`"
            type="button"
            class="observability-page__card"
            @click="page.openCurrentDetail(row)"
          >
            <div class="observability-page__card-top">
              <strong>{{ row.title }}</strong>
              <el-tag size="small" :type="row.statusType" effect="light">{{ row.statusText }}</el-tag>
            </div>
            <div class="observability-page__card-body">
              <span>{{ row.subtitle || `${row.category} · ${row.entityKey}` }}</span>
              <span>来源：{{ row.syncSourceLabel }}</span>
              <span>更新时间：{{ row.updatedAtLabel }}</span>
            </div>
          </button>
        </div>

        <div v-else-if="page.activeTab === 'history'" class="observability-page__cards">
          <button
            v-for="row in page.historyRows"
            :key="row.id"
            type="button"
            class="observability-page__card"
            @click="page.openHistoryDetail(row)"
          >
            <div class="observability-page__card-top">
              <strong>{{ row.title }}</strong>
              <el-tag size="small" :type="row.statusType" effect="light">{{ row.status }}</el-tag>
            </div>
            <div class="observability-page__card-body">
              <span>{{ row.entityType }} · {{ row.entityKey }}</span>
              <span>来源：{{ row.source || "-" }}</span>
              <span>时间：{{ row.occurredAtLabel }}</span>
            </div>
          </button>
        </div>

        <div v-else class="observability-page__cards">
          <button
            v-for="row in page.webhookRows"
            :key="row.id"
            type="button"
            class="observability-page__card"
            @click="page.openWebhookDetail(row)"
          >
            <div class="observability-page__card-top">
              <strong>{{ row.eventType || "未记录事件" }}</strong>
              <el-tag size="small" :type="row.statusType" effect="light">{{ row.status }}</el-tag>
            </div>
            <div class="observability-page__card-body">
              <span>{{ row.businessType }} · {{ row.businessKey || row.msgId || "-" }}</span>
              <span>阶段：{{ row.processStage || "-" }}</span>
              <span>接收时间：{{ row.receivedAtLabel }}</span>
            </div>
          </button>
        </div>
      </div>

      <el-empty
        v-if="!page.loading && page.listCount === 0"
        :description="props.mode === 'workspace' ? '当前筛选条件下没有记录。' : '当前没有匹配的失败记录。'"
      />

      <div class="observability-page__pagination">
        <el-pagination
          background
          layout="prev, pager, next"
          :current-page="page.currentPage"
          :page-size="page.pageSize"
          :total="page.total"
          @current-change="page.changePage"
        />
      </div>
    </el-card>

    <ObservabilityDetailDrawer
      :visible="page.drawerVisible"
      :loading="page.detailLoading"
      :title="page.detailTitle"
      :subtitle="page.detailSubtitle"
      :summary-lines="page.detailSummaryLines"
      :detail-fields="page.detailFields"
      :error-message="page.detailErrorMessage"
      @update:visible="updateDrawerVisible"
    />
  </section>
</template>

<style scoped>
.observability-page {
  display: grid;
  gap: 16px;
}

.observability-page__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.observability-page__metric {
  display: grid;
  gap: 8px;
}

.observability-page__metric-label {
  color: var(--yx-text-muted);
  font-size: 14px;
}

.observability-page__metric-value {
  font-size: 28px;
  line-height: 1;
}

.observability-page__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.observability-page__header p {
  margin: 6px 0 0;
  color: var(--yx-text-muted);
  font-size: 13px;
}

.observability-page__tabs {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.observability-page__filters {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.observability-page__desktop {
  display: block;
}

.observability-page__error {
  margin-bottom: 16px;
}

.observability-page__mobile {
  display: none;
}

.observability-page__title-button,
.observability-page__card {
  width: 100%;
  border: 0;
  padding: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.observability-page__title-button {
  display: grid;
  gap: 4px;
}

.observability-page__title-button span {
  color: var(--yx-text-muted);
  font-size: 12px;
}

.observability-page__pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.observability-page__cards {
  display: grid;
  gap: 12px;
}

.observability-page__card {
  padding: 14px;
  border: 1px solid var(--yx-border);
  border-radius: 12px;
  background: #fff;
}

.observability-page__card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.observability-page__card-body {
  margin-top: 10px;
  display: grid;
  gap: 4px;
  color: var(--yx-text-muted);
  font-size: 13px;
}

@media (max-width: 1199px) {
  .observability-page__summary,
  .observability-page__filters {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .observability-page__header {
    flex-direction: column;
  }

  .observability-page__tabs {
    justify-content: flex-start;
  }
}

@media (max-width: 767px) {
  .observability-page__summary,
  .observability-page__filters {
    grid-template-columns: minmax(0, 1fr);
  }

  .observability-page__desktop {
    display: none;
  }

  .observability-page__mobile {
    display: block;
  }

  .observability-page__pagination {
    justify-content: center;
  }
}
</style>
