<script setup lang="ts">
import { computed } from "vue";

import { parseMessageSegments } from "@/utils/umpParser";
import { useChatTestPage } from "./useChatTestPage";

const {
  sessions,
  messages,
  currentSessionId,
  draftInput,
  lastIntent,
  loadingSessions,
  loadingMessages,
  sending,
  messageViewport,
  hasSession,
  headerDescription,
  selectSession,
  startNewSession,
  sendMessage,
  saveCurrentSession,
  discardCurrentSession,
} = useChatTestPage();

const sessionCountText = computed(() => `${sessions.value.length} 个已保存会话`);

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

    <!-- 左侧会话列表 -->
    <aside class="ct-sidebar">
      <div class="ct-sidebar__head">
        <span class="ct-sidebar__title">历史会话</span>
        <el-button size="small" type="primary" plain @click="startNewSession">新建</el-button>
      </div>
      <div v-loading="loadingSessions" class="ct-sidebar__list">
        <el-empty
          v-if="!loadingSessions && sessions.length === 0"
          :image-size="60"
          description="暂无历史会话"
        />
        <button
          v-for="session in sessions"
          :key="session.id"
          type="button"
          class="ct-session"
          :class="{ 'ct-session--active': session.id === currentSessionId }"
          @click="selectSession(session)"
        >
          <div class="ct-session__name">{{ session.name }}</div>
          <div class="ct-session__meta">
            <span>{{ formatTime(session.createdAt) }}</span>
            <span>{{ session.msgCount }} 条</span>
          </div>
        </button>
      </div>
    </aside>

    <!-- 右侧主对话区 -->
    <div class="ct-main">
      <!-- 顶部标题栏（微信风格） -->
      <div class="ct-header">
        <div class="ct-header__center">
          <span class="ct-header__name">{{ headerDescription }}</span>
          <span v-if="lastIntent" class="ct-header__badge">意图：{{ lastIntent }}</span>
        </div>
        <div class="ct-header__actions">
          <el-button size="small" :disabled="!hasSession" @click="saveCurrentSession">保存</el-button>
          <el-button size="small" type="danger" plain @click="discardCurrentSession">丢弃</el-button>
        </div>
      </div>

      <!-- 消息流（固定高度，可滚动） -->
      <div ref="messageViewport" v-loading="loadingMessages" class="ct-messages">
        <el-empty
          v-if="!loadingMessages && messages.length === 0"
          :image-size="80"
          description="开始一段新的测试对话吧"
        />

        <div
          v-for="(message, index) in messages"
          :key="`${message.createdAt}-${index}`"
          class="ct-msg"
          :class="message.role === 'user' ? 'ct-msg--user' : 'ct-msg--ai'"
        >
          <div class="ct-msg__avatar">
            <span v-if="message.role === 'user'" class="avatar avatar--user">你</span>
            <span v-else class="avatar avatar--ai">芸</span>
          </div>
          <div class="ct-msg__body">
            <div class="ct-msg__bubble">
              <template v-for="(seg, si) in parseMessageSegments(message.content)" :key="si">
                <span v-if="seg.type === 'text'" class="ct-msg__text">{{ seg.value }}</span>
                <a
                  v-else-if="seg.type === 'card'"
                  :href="seg.url"
                  target="_blank"
                  rel="noopener"
                  class="ump-card"
                >
                  <img v-if="seg.src" :src="seg.src" :alt="seg.title" class="ump-card__img" />
                  <div class="ump-card__info">
                    <div class="ump-card__title">{{ seg.title }}</div>
                    <div class="ump-card__price">¥{{ seg.price }}</div>
                  </div>
                </a>
              </template>
            </div>
            <div v-if="message.createdAt" class="ct-msg__time">{{ formatTime(message.createdAt) }}</div>
          </div>
        </div>

        <!-- 打字中动画 -->
        <div v-if="sending" class="ct-msg ct-msg--ai ct-msg--typing">
          <div class="ct-msg__avatar"><span class="avatar avatar--ai">芸</span></div>
          <div class="ct-msg__body">
            <div class="ct-msg__bubble">
              <span class="typing-dot" /><span class="typing-dot" /><span class="typing-dot" />
            </div>
          </div>
        </div>
      </div>

      <!-- 底部输入栏（微信风格） -->
      <div class="ct-composer">
        <el-input
          v-model="draftInput"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 5 }"
          resize="none"
          placeholder="输入消息…  Enter 发送，Shift+Enter 换行"
          class="ct-composer__input"
          @keydown.enter.exact.prevent="sendMessage"
        />
        <el-button
          type="primary"
          :loading="sending"
          class="ct-composer__btn"
          @click="sendMessage"
        >
          发送
        </el-button>
      </div>
    </div>

  </section>
</template>

<style scoped>
/* ── 页面容器：固定高度，绝不随内容撑开 ── */
.chat-test-page {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 0;
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--yx-border);
  border-radius: 12px;
  background: #fff;
}

/* ── 左侧会话列表 ── */
.ct-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  border-right: 1px solid var(--yx-border);
  background: #f5f5f5;
}

.ct-sidebar__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--yx-border);
  flex-shrink: 0;
  background: #ededed;
}

.ct-sidebar__title {
  font-size: 14px;
  font-weight: 600;
  color: #555;
}

.ct-sidebar__list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

/* 会话列表项 — 统一高度 */
.ct-session {
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%;
  height: 64px;
  padding: 0 14px;
  border: none;
  border-bottom: 1px solid #e8e8e8;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
  flex-shrink: 0;
}

.ct-session:hover { background: #ebebeb; }
.ct-session--active { background: #d6f0e0; }

.ct-session__name {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ct-session__meta {
  margin-top: 3px;
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #999;
}

/* ── 右侧主对话区 ── */
.ct-main {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* 顶部标题栏 */
.ct-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--yx-border);
  background: #ededed;
  flex-shrink: 0;
  min-height: 48px;
}

.ct-header__center {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ct-header__name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
}

.ct-header__badge {
  font-size: 11px;
  color: #888;
}

.ct-header__actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* 消息流 — flex:1 撑满剩余高度，overflow:auto 独立滚动 */
.ct-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: #ededed;
}

/* 单条消息 */
.ct-msg {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  max-width: 78%;
}

.ct-msg--user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.ct-msg--ai {
  align-self: flex-start;
}

.ct-msg__avatar { flex-shrink: 0; }

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
}
.avatar--user { background: #576b95; }
.avatar--ai   { background: #07c160; }

.ct-msg__body {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.ct-msg--user .ct-msg__body { align-items: flex-end; }

.ct-msg__bubble {
  position: relative;
  display: inline-block;
  padding: 9px 13px;
  font-size: 14px;
  line-height: 1.65;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(0,0,0,.08);
}

/* AI 气泡 */
.ct-msg--ai .ct-msg__bubble {
  background: #fff;
  color: #1a1a1a;
  border-radius: 0 8px 8px 8px;
}
.ct-msg--ai .ct-msg__bubble::before {
  content: '';
  position: absolute;
  top: 10px;
  left: -6px;
  border: 6px solid transparent;
  border-right-color: #fff;
  border-left: 0;
}

/* 用户气泡 */
.ct-msg--user .ct-msg__bubble {
  background: #95ec69;
  color: #1a1a1a;
  border-radius: 8px 0 8px 8px;
}
.ct-msg--user .ct-msg__bubble::after {
  content: '';
  position: absolute;
  top: 10px;
  right: -6px;
  border: 6px solid transparent;
  border-left-color: #95ec69;
  border-right: 0;
}

.ct-msg__text { white-space: pre-wrap; }

.ct-msg__time {
  font-size: 11px;
  color: #aaa;
  padding: 0 2px;
}

/* 打字动画气泡 */
.ct-msg--typing .ct-msg__bubble {
  display: inline-flex;
  gap: 5px;
  align-items: center;
  padding: 13px 16px;
}

.typing-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #aaa;
  animation: typing-bounce 1.2s infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: .5; }
  40% { transform: translateY(-5px); opacity: 1; }
}

/* ── 底部输入栏 ── */
.ct-composer {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 10px 14px;
  border-top: 1px solid #d0d0d0;
  background: #f5f5f5;
  flex-shrink: 0;
}

.ct-composer__input {
  flex: 1;
}

.ct-composer__btn {
  flex-shrink: 0;
  height: 36px;
  padding: 0 18px;
}

/* ── 商品卡片 ── */
.ump-card {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  padding: 8px 10px;
  background: #f0f0f0;
  border-radius: 8px;
  border: 1px solid #ddd;
  text-decoration: none;
  color: inherit;
  transition: background 0.15s;
  max-width: 240px;
}
.ump-card:hover { background: #e8e8e8; }
.ump-card + .ump-card { margin-top: 6px; }

.ump-card__img {
  width: 54px;
  height: 54px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
}

.ump-card__info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.ump-card__title {
  font-size: 12px;
  font-weight: 600;
  color: #1a1a1a;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.ump-card__price {
  font-size: 13px;
  font-weight: 700;
  color: #e6333a;
}

/* ── 响应式 ── */
@media (max-width: 900px) {
  .chat-test-page {
    grid-template-columns: minmax(0, 1fr);
  }
  .ct-sidebar {
    display: none;
  }
}
</style>
