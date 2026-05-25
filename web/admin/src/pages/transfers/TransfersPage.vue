<script setup lang="ts">
import { computed, onMounted } from "vue";

import TransferDetailDrawer from "@/features/transfers/TransferDetailDrawer.vue";

import { useTransfersPage } from "./useTransfersPage";

const {
  loading,
  actionLoadingId,
  detailLoading,
  replySending,
  drawerVisible,
  replyDraft,
  transfers,
  selectedTransfer,
  sessionMessages,
  pendingCount,
  acceptedCount,
  listRows,
  normalizeRole,
  loadTransfers,
  openDetail,
  closeDrawer,
  acceptSelectedTransfer,
  closeSelectedTransfer,
  sendReply,
} = useTransfersPage();

const totalCount = computed(() => transfers.value.length);

onMounted(async () => {
  await loadTransfers();
});

function updateReplyDraft(value: string) {
  replyDraft.value = value;
}
</script>

<template>
  <section class="transfers-page">
    <div class="transfers-page__summary">
      <el-card shadow="never">
        <div class="transfers-page__metric">
          <span class="transfers-page__metric-label">当前队列</span>
          <strong class="transfers-page__metric-value">{{ totalCount }}</strong>
        </div>
      </el-card>
      <el-card shadow="never">
        <div class="transfers-page__metric">
          <span class="transfers-page__metric-label">待处理</span>
          <strong class="transfers-page__metric-value">{{ page.pendingCount }}</strong>
        </div>
      </el-card>
      <el-card shadow="never">
        <div class="transfers-page__metric">
          <span class="transfers-page__metric-label">本页已接单</span>
          <strong class="transfers-page__metric-value">{{ page.acceptedCount }}</strong>
        </div>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="transfers-page__header">
          <div>
            <strong>转人工队列</strong>
            <p>先承接当前待处理请求，支持查看会话、人工回复、接单和关闭。</p>
          </div>
          <el-button :loading="loading" @click="loadTransfers">刷新队列</el-button>
        </div>
      </template>

      <div class="transfers-page__desktop">
        <el-table :data="listRows" v-loading="loading" stripe>
          <el-table-column prop="shortUserId" label="用户" min-width="170" />
          <el-table-column prop="reason" label="转人工原因" min-width="240" show-overflow-tooltip />
          <el-table-column prop="conversationSummary" label="会话摘要" min-width="280" show-overflow-tooltip />
          <el-table-column prop="statusLabel" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'accepted' ? 'success' : 'warning'" effect="light">
                {{ row.statusLabel }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="创建时间" min-width="180">
            <template #default="{ row }">
              {{ row.createdAt ? row.createdAt.replace("T", " ").slice(0, 19) : "未记录" }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <div class="transfers-page__actions">
                <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
                <el-button
                  size="small"
                  type="success"
                  plain
                  :disabled="row.status !== 'pending'"
                  :loading="actionLoadingId === row.id && row.status === 'pending'"
                  @click="openDetail(row)"
                >
                  处理
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="transfers-page__mobile">
        <el-skeleton :rows="4" animated v-if="loading" />
        <div v-else class="transfers-page__cards">
          <button
            v-for="row in listRows"
            :key="row.id"
            type="button"
            class="transfers-page__card"
            @click="openDetail(row)"
          >
            <div class="transfers-page__card-top">
              <strong>{{ row.shortUserId }}</strong>
              <el-tag size="small" :type="row.status === 'accepted' ? 'success' : 'warning'" effect="light">
                {{ row.statusLabel }}
              </el-tag>
            </div>
            <div class="transfers-page__card-body">
              <span>原因：{{ row.reason }}</span>
              <span v-if="row.conversationSummary">摘要：{{ row.conversationSummary }}</span>
              <span>时间：{{ row.createdAt ? row.createdAt.replace("T", " ").slice(0, 19) : "未记录" }}</span>
            </div>
          </button>
        </div>
      </div>

      <el-empty
        v-if="!loading && listRows.length === 0"
        description="当前没有待处理的转人工请求"
      />
    </el-card>

    <TransferDetailDrawer
      :visible="drawerVisible"
      :transfer="selectedTransfer"
      :loading="detailLoading"
      :action-loading-id="actionLoadingId"
      :reply-sending="replySending"
      :reply-draft="replyDraft"
      :messages="sessionMessages"
      :normalize-role="normalizeRole"
      @update:visible="($event) => (!$event ? closeDrawer() : null)"
      @update:reply-draft="updateReplyDraft"
      @accept="acceptSelectedTransfer"
      @close="closeSelectedTransfer"
      @send-reply="sendReply"
    />
  </section>
</template>

<style scoped>
.transfers-page {
  display: grid;
  gap: 16px;
}

.transfers-page__summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.transfers-page__metric {
  display: grid;
  gap: 8px;
}

.transfers-page__metric-label {
  color: var(--yx-text-muted);
  font-size: 14px;
}

.transfers-page__metric-value {
  font-size: 28px;
  line-height: 1;
}

.transfers-page__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.transfers-page__header p {
  margin: 6px 0 0;
  color: var(--yx-text-muted);
  font-size: 13px;
}

.transfers-page__desktop {
  display: block;
}

.transfers-page__mobile {
  display: none;
}

.transfers-page__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.transfers-page__cards {
  display: grid;
  gap: 12px;
}

.transfers-page__card {
  width: 100%;
  border: 1px solid var(--yx-border);
  border-radius: 12px;
  padding: 14px;
  background: #fff;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.transfers-page__card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.transfers-page__card-body {
  margin-top: 10px;
  display: grid;
  gap: 4px;
  color: var(--yx-text-muted);
  font-size: 13px;
}

@media (max-width: 1199px) {
  .transfers-page__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 767px) {
  .transfers-page__summary {
    grid-template-columns: minmax(0, 1fr);
  }

  .transfers-page__desktop {
    display: none;
  }

  .transfers-page__mobile {
    display: block;
  }
}
</style>
