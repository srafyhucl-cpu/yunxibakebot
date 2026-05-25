<script setup lang="ts">
import { computed } from "vue";

import { useChatTestPage } from "./useChatTestPage";

const page = useChatTestPage();

const sessionCountText = computed(() => `${page.sessions.value.length} 个已保存会话`);

function formatTime(value: string) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
</script>

<template>
  <section class="chat-test-page">
    <aside class="chat-test-page__sidebar">
      <el-card shadow="never" class="chat-test-panel">
        <template #header>
          <div class="chat-test-panel__header">
            <div>
              <div class="chat-test-panel__title">会话列表</div>
              <div class="chat-test-panel__meta">{{ sessionCountText }}</div>
            </div>
            <el-button type="primary" plain @click="page.startNewSession">
              新建会话
            </el-button>
          </div>
        </template>

        <div v-loading="page.loadingSessions" class="chat-session-list">
          <button
            v-for="session in page.sessions"
            :key="session.id"
            type="button"
            class="chat-session-item"
            :class="{ 'chat-session-item--active': session.id === page.currentSessionId }"
            @click="page.selectSession(session)"
          >
            <div class="chat-session-item__title">{{ session.name }}</div>
            <div class="chat-session-item__meta">
              <span>{{ formatTime(session.createdAt) }}</span>
              <span>{{ session.msgCount }} 条</span>
            </div>
          </button>

          <el-empty
            v-if="!page.loadingSessions && page.sessions.length === 0"
            description="还没有已保存的测试会话"
          />
        </div>
      </el-card>
    </aside>

    <div class="chat-test-page__main">
      <el-card shadow="never" class="chat-test-panel chat-test-panel--conversation">
        <template #header>
          <div class="chat-test-panel__header chat-test-panel__header--conversation">
            <div>
              <div class="chat-test-panel__title">{{ page.headerDescription }}</div>
              <div class="chat-test-panel__meta">
                <span v-if="page.lastIntent">意图：{{ page.lastIntent }}</span>
                <span v-else>发送一条消息后会显示识别意图</span>
              </div>
            </div>
            <div class="chat-test-panel__actions">
              <el-button :disabled="!page.hasSession" @click="page.saveCurrentSession">
                保存会话
              </el-button>
              <el-button danger plain @click="page.discardCurrentSession">
                丢弃会话
              </el-button>
            </div>
          </div>
        </template>

        <div
          ref="page.messageViewport"
          v-loading="page.loadingMessages"
          class="chat-message-list"
        >
          <div
            v-for="(message, index) in page.messages"
            :key="`${message.createdAt}-${index}`"
            class="chat-message"
            :class="{
              'chat-message--user': message.role === 'user',
              'chat-message--assistant': message.role !== 'user',
            }"
          >
            <div class="chat-message__role">
              {{ message.role === "user" ? "你" : "AI" }}
            </div>
            <div class="chat-message__bubble">
              <div class="chat-message__content">{{ message.content }}</div>
              <div class="chat-message__time">{{ formatTime(message.createdAt) }}</div>
            </div>
          </div>

          <el-empty
            v-if="!page.loadingMessages && page.messages.length === 0"
            description="开始一段新的测试对话吧"
          />
        </div>

        <div class="chat-composer">
          <el-input
            v-model="page.draftInput"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            resize="none"
            placeholder="输入一条测试消息，例如：今天下单最快什么时候能送到？"
            @keydown.enter.exact.prevent="page.sendMessage"
          />
          <div class="chat-composer__footer">
            <span class="chat-composer__hint">
              Enter 发送，Shift + Enter 换行
            </span>
            <el-button
              type="primary"
              :loading="page.sending"
              @click="page.sendMessage"
            >
              发送消息
            </el-button>
          </div>
        </div>
      </el-card>
    </div>
  </section>
</template>

<style scoped>
.chat-test-page {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  min-height: calc(100vh - 140px);
}

.chat-test-page__sidebar,
.chat-test-page__main,
.chat-test-panel,
.chat-test-panel--conversation {
  min-height: 0;
}

.chat-test-panel {
  border-radius: 16px;
}

.chat-test-panel--conversation {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-test-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chat-test-panel__header--conversation {
  align-items: flex-start;
}

.chat-test-panel__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--yx-text);
}

.chat-test-panel__meta {
  margin-top: 6px;
  font-size: 13px;
  color: var(--yx-text-muted);
}

.chat-test-panel__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.chat-session-list {
  display: grid;
  gap: 10px;
}

.chat-session-item {
  width: 100%;
  border: 1px solid var(--yx-border);
  border-radius: 12px;
  padding: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.chat-session-item:hover {
  border-color: rgba(236, 111, 94, 0.4);
  box-shadow: var(--yx-shadow);
  transform: translateY(-1px);
}

.chat-session-item--active {
  border-color: var(--yx-brand);
  background: var(--yx-brand-soft);
}

.chat-session-item__title {
  font-size: 15px;
  font-weight: 600;
}

.chat-session-item__meta {
  margin-top: 6px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: var(--yx-text-muted);
}

.chat-message-list {
  flex: 1;
  overflow: auto;
  padding: 4px 2px 8px;
  display: grid;
  gap: 14px;
}

.chat-message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.chat-message--user {
  justify-content: flex-end;
}

.chat-message__role {
  min-width: 32px;
  padding-top: 8px;
  font-size: 12px;
  color: var(--yx-text-muted);
}

.chat-message__bubble {
  max-width: min(720px, 100%);
  border-radius: 16px;
  padding: 14px 16px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.chat-message--assistant .chat-message__bubble {
  background: #fff;
  border: 1px solid var(--yx-border);
}

.chat-message--user .chat-message__bubble {
  background: var(--yx-brand);
  color: #fff;
}

.chat-message__content {
  white-space: pre-wrap;
  line-height: 1.7;
}

.chat-message__time {
  margin-top: 10px;
  font-size: 12px;
  opacity: 0.72;
}

.chat-composer {
  margin-top: 16px;
  border-top: 1px solid var(--yx-border);
  padding-top: 16px;
}

.chat-composer__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
}

.chat-composer__hint {
  font-size: 12px;
  color: var(--yx-text-muted);
}

@media (max-width: 1199px) {
  .chat-test-page {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .chat-test-page {
    min-height: auto;
  }

  .chat-test-panel__header,
  .chat-composer__footer {
    flex-direction: column;
    align-items: stretch;
  }

  .chat-message__bubble {
    max-width: 100%;
  }
}
</style>
