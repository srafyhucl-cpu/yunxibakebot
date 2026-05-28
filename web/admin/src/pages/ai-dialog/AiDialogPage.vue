<script setup lang="ts">
import { parseMessageSegments } from "@/utils/umpParser";
import { useAiDialogPage } from "./useAiDialogPage";

const {
  sessions, messages, currentSessionId, currentDisplay,
  draftInput, lastIntent, loadingSessions, loadingMessages,
  sending, messageViewport, hasSession, headerTitle,
  showRolePicker, selectedRole, customRole, pickerValid, PRESET_ROLES,
  ctxVisible, ctxX, ctxY, ctxSession,
  mobileChatActive,
  openSession, onNewChat, selectPreset, onCustomInput,
  cancelRolePicker, confirmRolePicker,
  sendMessage, showCtxMenu, lpStart, lpEnd,
  ctxPinSession, ctxDeleteSession, mobileBack,
} = useAiDialogPage();

import type { AiDialogSession } from "@/types/aiDialog";

function sessionLabel(s: AiDialogSession): string {
  return s.name || s.userDisplay || s.userId;
}

function sessionAvatarChar(s: AiDialogSession): string {
  const label = sessionLabel(s);
  return label ? label[0].toUpperCase() : "?";
}

const AVATAR_COLORS = ["#5c9ee6","#e67c5c","#5cbe8c","#a068d4","#e6a83a","#5cb8d4","#d45c8c","#7db35c"];
function sessionAvatarColor(s: AiDialogSession): string {
  const label = sessionLabel(s);
  let h = 0;
  for (let i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
}

function fmtTime(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return "";
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000 && d.getDate() === now.getDate()) return d.toTimeString().slice(0, 5);
  if (diff < 172800000) return "昨天";
  const days = ["日","一","二","三","四","五","六"];
  if (diff < 604800000) return "周" + days[d.getDay()];
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

const INTENT_LABELS: Record<string | number, string> = {
  1:"商品咨询", 2:"规则咨询", 3:"运费费用", 4:"配送履约",
  5:"订单办理", 6:"售后异常", 7:"人工服务", 8:"闲聊其他",
};
</script>

<template>
  <section class="ctp" :class="{ 'ctp--chat': mobileChatActive }">

    <!-- ===== 左侧对话列表 ===== -->
    <aside class="ctp-sb">
      <div class="ctp-sb__hd">
        <span class="ctp-sb__title">AI 对话</span>
        <el-button size="small" type="primary" plain @click="onNewChat">＋ 新建</el-button>
      </div>
      <div v-loading="loadingSessions" class="ctp-sb__list">
        <el-empty
          v-if="!loadingSessions && sessions.length === 0"
          :image-size="56"
          description="暂无对话，点击新建"
        />
        <button
          v-for="s in sessions"
          :key="s.id"
          type="button"
          class="conv-item"
          :class="{ 'conv-item--active': s.id === currentSessionId, 'conv-item--pinned': s.pinned }"
          @click="openSession(s)"
          @contextmenu.prevent="showCtxMenu($event, s)"
          @touchstart.passive="lpStart($event, s)"
          @touchend.passive="lpEnd()"
          @touchmove.passive="lpEnd()"
        >
          <div class="conv-ava" :style="{ background: sessionAvatarColor(s) }">
            {{ sessionAvatarChar(s) }}
            <span v-if="s.pinned" class="conv-pin">📌</span>
          </div>
          <div class="conv-body">
            <div class="conv-top">
              <span class="conv-name">{{ sessionLabel(s) }}</span>
              <span class="conv-time">{{ fmtTime(s.updatedAt || s.createdAt) }}</span>
            </div>
            <div class="conv-prev">{{ s.lastMsg || '\u200b' }}</div>
          </div>
        </button>
      </div>
    </aside>

    <!-- ===== 右侧聊天区 ===== -->
    <div class="ctp-main">
      <div v-if="!hasSession && !messages.length" class="ctp-empty">
        <el-empty :image-size="80" description="选择一个对话，或点击「新建」开始" />
      </div>

      <template v-else>
        <!-- 顶栏 -->
        <div class="ctp-hd">
          <button class="ctp-back" @click="mobileBack">‹</button>
          <div class="ctp-hd__center">
            <span class="ctp-hd__name">{{ headerTitle }}</span>
            <span v-if="lastIntent" class="ctp-hd__badge">
              意图：{{ INTENT_LABELS[lastIntent] || lastIntent }}
            </span>
          </div>
          <div style="width:40px;" />
        </div>

        <!-- 消息流 -->
        <div ref="messageViewport" v-loading="loadingMessages" class="ctp-msgs">
          <div
            v-for="(msg, idx) in messages"
            :key="`${msg.createdAt}-${idx}`"
            class="ct-msg"
            :class="msg.role === 'user' ? 'ct-msg--user' : 'ct-msg--ai'"
          >
            <div class="ct-msg__avatar">
              <span v-if="msg.role === 'user'" class="avatar avatar--user">你</span>
              <span v-else class="avatar avatar--ai">芸</span>
            </div>
            <div class="ct-msg__body">
              <div class="ct-msg__bubble">
                <template v-for="(seg, si) in parseMessageSegments(msg.content)" :key="si">
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
              <div v-if="msg.createdAt" class="ct-msg__time">{{ fmtTime(msg.createdAt) }}</div>
            </div>
          </div>

          <div v-if="sending" class="ct-msg ct-msg--ai ct-msg--typing">
            <div class="ct-msg__avatar"><span class="avatar avatar--ai">芸</span></div>
            <div class="ct-msg__body">
              <div class="ct-msg__bubble">
                <span class="typing-dot" /><span class="typing-dot" /><span class="typing-dot" />
              </div>
            </div>
          </div>
        </div>

        <!-- 输入栏 -->
        <div class="ctp-composer">
          <el-input
            v-model="draftInput"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 5 }"
            resize="none"
            placeholder="输入消息…  Enter 发送，Shift+Enter 换行"
            class="ctp-composer__input"
            @keydown.enter.exact.prevent="sendMessage"
          />
          <el-button type="primary" :loading="sending" class="ctp-composer__btn" @click="sendMessage">
            发送
          </el-button>
        </div>
      </template>
    </div>

    <!-- ===== 角色选择弹窗 ===== -->
    <el-dialog
      v-model="showRolePicker"
      title="选择用户角色"
      width="420px"
      :close-on-click-modal="false"
      align-center
    >
      <p class="rp-sub">模拟不同类型顾客发起测试对话</p>
      <div class="rp-presets">
        <button
          v-for="role in PRESET_ROLES"
          :key="role"
          class="rp-tag"
          :class="{ 'rp-tag--sel': selectedRole === role }"
          @click="selectPreset(role)"
        >
          {{ role }}
        </button>
      </div>
      <div class="rp-divider">或自定义</div>
      <el-input
        v-model="customRole"
        placeholder="输入自定义名称…"
        clearable
        @input="onCustomInput(customRole)"
      />
      <template #footer>
        <el-button @click="cancelRolePicker">退出</el-button>
        <el-button type="primary" :disabled="!pickerValid" @click="confirmRolePicker">
          开始对话
        </el-button>
      </template>
    </el-dialog>

    <!-- ===== 右键/长按上下文菜单 ===== -->
    <div
      v-if="ctxVisible"
      class="ctx-menu"
      :style="{ left: ctxX + 'px', top: ctxY + 'px' }"
      @click.stop
    >
      <button class="ctx-item" @click="ctxPinSession">
        {{ ctxSession?.pinned ? '取消置顶' : '置顶对话' }}
      </button>
      <button class="ctx-item ctx-item--danger" @click="ctxDeleteSession">删除对话</button>
    </div>

  </section>
</template>

<style scoped>
.ctp {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  height: 100%;
  overflow: hidden;
  border: 1px solid var(--yx-border);
  border-radius: 12px;
  background: #fff;
  position: relative;
}

.ctp-sb {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  border-right: 1px solid var(--yx-border);
  background: #f5f5f5;
}

.ctp-sb__hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--yx-border);
  flex-shrink: 0;
  background: #ededed;
}

.ctp-sb__title { font-size: 14px; font-weight: 600; color: #555; }

.ctp-sb__list { flex: 1; overflow-y: auto; padding: 4px 0; }

.conv-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: none;
  border-bottom: 1px solid rgba(0,0,0,0.04);
  background: transparent;
  text-align: left;
  cursor: pointer;
  -webkit-user-select: none;
  user-select: none;
  transition: background 0.12s;
}

.conv-item:hover { background: rgba(0,0,0,0.04); }
.conv-item--active { background: #c8edba; }
.conv-item--pinned:not(.conv-item--active) { background: #f4f4f4; }

.conv-ava {
  width: 40px; height: 40px; border-radius: 4px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; color: #fff; position: relative;
}

.conv-pin { position: absolute; top: -4px; right: -4px; font-size: 9px; line-height: 1; }

.conv-body { flex: 1; min-width: 0; }
.conv-top { display: flex; justify-content: space-between; align-items: baseline; }
.conv-name {
  font-size: 14px; font-weight: 500; color: #191919;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 130px;
}
.conv-time { font-size: 11px; color: #aaa; flex-shrink: 0; margin-left: 4px; }
.conv-prev { font-size: 12px; color: #aaa; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }

.ctp-main { display: flex; flex-direction: column; height: 100%; overflow: hidden; }

.ctp-empty { flex: 1; display: flex; align-items: center; justify-content: center; }

.ctp-hd {
  display: flex; align-items: center; padding: 0 10px; height: 50px;
  border-bottom: 1px solid var(--yx-border); background: #ededed; flex-shrink: 0;
}

.ctp-back {
  display: none; border: none; background: none; font-size: 26px; line-height: 1;
  color: #555; cursor: pointer; padding: 4px 8px 4px 2px;
}

.ctp-hd__center { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 2px; }
.ctp-hd__name { font-size: 15px; font-weight: 600; color: #1a1a1a; }
.ctp-hd__badge { font-size: 11px; color: #888; }

.ctp-msgs {
  flex: 1; overflow-y: auto; padding: 16px 14px;
  display: flex; flex-direction: column; gap: 16px; background: #ededed;
}

.ct-msg { display: flex; gap: 10px; align-items: flex-start; max-width: 78%; }
.ct-msg--user { align-self: flex-end; flex-direction: row-reverse; }
.ct-msg--ai   { align-self: flex-start; }
.ct-msg__avatar { flex-shrink: 0; }

.avatar {
  display: flex; align-items: center; justify-content: center;
  width: 38px; height: 38px; border-radius: 6px;
  font-size: 13px; font-weight: 700; color: #fff;
}
.avatar--user { background: #576b95; }
.avatar--ai   { background: #07c160; }

.ct-msg__body { display: flex; flex-direction: column; gap: 3px; }
.ct-msg--user .ct-msg__body { align-items: flex-end; }

.ct-msg__bubble {
  position: relative; display: inline-block; padding: 9px 13px;
  font-size: 14px; line-height: 1.65; word-break: break-word;
  box-shadow: 0 1px 2px rgba(0,0,0,.08);
}
.ct-msg--ai .ct-msg__bubble {
  background: #fff; color: #1a1a1a; border-radius: 0 8px 8px 8px;
}
.ct-msg--ai .ct-msg__bubble::before {
  content: ''; position: absolute; top: 10px; left: -6px;
  border: 6px solid transparent; border-right-color: #fff; border-left: 0;
}
.ct-msg--user .ct-msg__bubble {
  background: #95ec69; color: #1a1a1a; border-radius: 8px 0 8px 8px;
}
.ct-msg--user .ct-msg__bubble::after {
  content: ''; position: absolute; top: 10px; right: -6px;
  border: 6px solid transparent; border-left-color: #95ec69; border-right: 0;
}
.ct-msg__text { white-space: pre-wrap; }
.ct-msg__time { font-size: 11px; color: #aaa; padding: 0 2px; }

.ct-msg--typing .ct-msg__bubble {
  display: inline-flex; gap: 5px; align-items: center; padding: 13px 16px;
}
.typing-dot {
  display: inline-block; width: 7px; height: 7px; border-radius: 50%;
  background: #aaa; animation: typing-bounce 1.2s infinite;
}
.typing-dot:nth-child(2) { animation-delay: .2s; }
.typing-dot:nth-child(3) { animation-delay: .4s; }
@keyframes typing-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: .5; }
  40%           { transform: translateY(-5px); opacity: 1; }
}

.ctp-composer {
  display: flex; align-items: flex-end; gap: 10px; padding: 10px 14px;
  border-top: 1px solid #d0d0d0; background: #f5f5f5; flex-shrink: 0;
}
.ctp-composer__input { flex: 1; }
.ctp-composer__btn { flex-shrink: 0; height: 36px; padding: 0 18px; }

.ump-card {
  display: flex; align-items: center; gap: 10px; margin-top: 8px; padding: 8px 10px;
  background: #f0f0f0; border-radius: 8px; border: 1px solid #ddd;
  text-decoration: none; color: inherit; max-width: 240px;
}
.ump-card:hover { background: #e8e8e8; }
.ump-card__img { width: 54px; height: 54px; object-fit: cover; border-radius: 6px; flex-shrink: 0; }
.ump-card__info { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.ump-card__title {
  font-size: 12px; font-weight: 600; color: #1a1a1a;
  overflow: hidden; text-overflow: ellipsis;
  display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical;
}
.ump-card__price { font-size: 13px; font-weight: 700; color: #e6333a; }

.rp-sub { font-size: 13px; color: #999; margin-bottom: 14px; }
.rp-presets { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.rp-tag {
  border: 1.5px solid #e0e0e0; background: #fff; border-radius: 20px;
  padding: 6px 14px; font-size: 14px; cursor: pointer; color: #333;
  transition: border-color .15s, background .15s, color .15s;
}
.rp-tag:hover { border-color: #07c160; color: #07c160; }
.rp-tag--sel { border-color: #07c160; background: #e8f9ef; color: #07c160; font-weight: 600; }
.rp-divider {
  display: flex; align-items: center; gap: 8px; color: #ccc;
  font-size: 12px; margin: 12px 0 10px;
}
.rp-divider::before, .rp-divider::after { content: ""; flex: 1; height: 1px; background: #eee; }

.ctx-menu {
  position: fixed; z-index: 9999; background: #fff;
  border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,.16);
  overflow: hidden; min-width: 120px;
}
.ctx-item {
  display: block; width: 100%; padding: 12px 18px; border: none;
  background: none; text-align: left; font-size: 14px; cursor: pointer; color: #333;
}
.ctx-item:hover { background: #f5f5f5; }
.ctx-item--danger { color: #e74c3c; }

@media (max-width: 900px) {
  .ctp { grid-template-columns: minmax(0, 1fr); }
  .ctp-sb { display: flex; }
  .ctp-main { display: none; }
  .ctp--chat .ctp-sb { display: none; }
  .ctp--chat .ctp-main { display: flex; }
  .ctp-back { display: block; }
}
</style>
