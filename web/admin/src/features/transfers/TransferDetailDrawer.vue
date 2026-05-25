<script setup lang="ts">
import { computed } from "vue";

import type { SessionMessage, TransferListItem } from "@/types/transfer";

const props = defineProps<{
  visible: boolean;
  transfer: TransferListItem | null;
  loading: boolean;
  actionLoadingId: string;
  replySending: boolean;
  replyDraft: string;
  messages: SessionMessage[];
  normalizeRole: (role: string) => string;
}>();

const emit = defineEmits<{
  (event: "update:visible", value: boolean): void;
  (event: "update:replyDraft", value: string): void;
  (event: "accept"): void;
  (event: "close"): void;
  (event: "send-reply"): void;
}>();

const isCurrentActionLoading = computed(
  () => props.transfer && props.actionLoadingId === props.transfer.id,
);

const title = computed(() => {
  if (!props.transfer) {
    return "转人工详情";
  }
  return `会话 ${props.transfer.sessionId.slice(0, 8)}`;
});

function updateVisible(value: boolean) {
  emit("update:visible", value);
}

function updateReplyDraft(value: string) {
  emit("update:replyDraft", value);
}
</script>

<template>
  <el-drawer
    :model-value="visible"
    :title="title"
    size="min(560px, 100%)"
    destroy-on-close
    @update:model-value="updateVisible"
  >
    <div v-if="transfer" class="transfer-detail">
      <el-card shadow="never" class="transfer-detail__summary">
        <div class="transfer-detail__summary-grid">
          <div>
            <span class="transfer-detail__label">用户</span>
            <strong>{{ transfer.userId }}</strong>
          </div>
          <div>
            <span class="transfer-detail__label">状态</span>
            <el-tag :type="transfer.status === 'accepted' ? 'success' : 'warning'" effect="light">
              {{ transfer.status === "accepted" ? "已接单" : "待处理" }}
            </el-tag>
          </div>
          <div>
            <span class="transfer-detail__label">创建时间</span>
            <strong>{{ transfer.createdAt ? transfer.createdAt.replace("T", " ").slice(0, 19) : "未记录" }}</strong>
          </div>
        </div>
        <div class="transfer-detail__reason">
          <span class="transfer-detail__label">转人工原因</span>
          <p>{{ transfer.reason || "未记录原因" }}</p>
        </div>
        <div v-if="transfer.conversationSummary" class="transfer-detail__reason">
          <span class="transfer-detail__label">会话摘要</span>
          <p>{{ transfer.conversationSummary }}</p>
        </div>
        <div class="transfer-detail__actions">
          <el-button
            type="success"
            plain
            :loading="isCurrentActionLoading && transfer.status === 'pending'"
            :disabled="transfer.status !== 'pending'"
            @click="$emit('accept')"
          >
            接单
          </el-button>
          <el-button
            type="danger"
            plain
            :loading="isCurrentActionLoading && transfer.status !== 'pending'"
            @click="$emit('close')"
          >
            关闭
          </el-button>
        </div>
      </el-card>

      <el-card shadow="never" class="transfer-detail__messages">
        <template #header>
          <div class="transfer-detail__card-header">
            <strong>会话消息</strong>
            <span>{{ messages.length }} 条</span>
          </div>
        </template>

        <div v-loading="loading" class="transfer-detail__message-list">
          <div
            v-for="(message, index) in messages"
            :key="`${message.createdAt}-${index}`"
            class="transfer-detail__message"
            :class="{
              'transfer-detail__message--user': message.role === 'user',
              'transfer-detail__message--assistant': message.role !== 'user',
            }"
          >
            <div class="transfer-detail__message-role">{{ normalizeRole(message.role) }}</div>
            <div class="transfer-detail__message-bubble">
              <div>{{ message.content }}</div>
              <small>{{ message.createdAt ? message.createdAt.replace("T", " ").slice(0, 19) : "" }}</small>
            </div>
          </div>

          <el-empty
            v-if="!loading && messages.length === 0"
            description="当前会话还没有可显示的消息"
          />
        </div>
      </el-card>

      <el-card shadow="never" class="transfer-detail__reply">
        <template #header>
          <div class="transfer-detail__card-header">
            <strong>人工回复</strong>
            <span>发送后会写入当前会话</span>
          </div>
        </template>

        <div class="transfer-detail__reply-body">
          <el-input
            :model-value="replyDraft"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            resize="none"
            placeholder="输入人工回复内容"
            @update:model-value="updateReplyDraft"
            @keydown.enter.exact.prevent="$emit('send-reply')"
          />
          <div class="transfer-detail__reply-footer">
            <span>Enter 发送，Shift + Enter 换行</span>
            <el-button type="primary" :loading="replySending" @click="$emit('send-reply')">
              发送回复
            </el-button>
          </div>
        </div>
      </el-card>
    </div>
  </el-drawer>
</template>

<style scoped>
.transfer-detail {
  display: grid;
  gap: 16px;
}

.transfer-detail__summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.transfer-detail__label {
  display: block;
  margin-bottom: 6px;
  color: var(--yx-text-muted);
  font-size: 12px;
}

.transfer-detail__reason {
  margin-top: 14px;
}

.transfer-detail__reason p {
  margin: 0;
  line-height: 1.6;
}

.transfer-detail__actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.transfer-detail__card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--yx-text-muted);
  font-size: 13px;
}

.transfer-detail__message-list {
  display: grid;
  gap: 12px;
  max-height: 360px;
  overflow: auto;
}

.transfer-detail__message {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.transfer-detail__message--user {
  justify-content: flex-end;
}

.transfer-detail__message-role {
  min-width: 32px;
  padding-top: 6px;
  font-size: 12px;
  color: var(--yx-text-muted);
}

.transfer-detail__message-bubble {
  max-width: calc(100% - 42px);
  display: grid;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #f7f7f9;
  line-height: 1.6;
}

.transfer-detail__message--user .transfer-detail__message-bubble {
  background: var(--yx-brand-soft);
}

.transfer-detail__message-bubble small {
  color: var(--yx-text-muted);
  font-size: 12px;
}

.transfer-detail__reply-body {
  display: grid;
  gap: 10px;
}

.transfer-detail__reply-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--yx-text-muted);
  font-size: 12px;
}

@media (max-width: 767px) {
  .transfer-detail__summary-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .transfer-detail__reply-footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
