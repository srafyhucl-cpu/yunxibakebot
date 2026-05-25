import { computed, nextTick, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { chatTestService } from "@/services/chatTest";
import type { ChatTestMessage, ChatTestSessionSummary } from "@/types/chatTest";

function buildDraftUserId() {
  return `admin_tester_${Date.now().toString(36)}`;
}

export function useChatTestPage() {
  const sessions = ref<ChatTestSessionSummary[]>([]);
  const messages = ref<ChatTestMessage[]>([]);
  const currentUserId = ref(buildDraftUserId());
  const currentSessionId = ref("");
  const currentSessionName = ref("");
  const draftInput = ref("");
  const lastIntent = ref("");
  const loadingSessions = ref(false);
  const loadingMessages = ref(false);
  const sending = ref(false);
  const messageViewport = ref<HTMLElement | null>(null);

  const hasSession = computed(() => currentSessionId.value.length > 0);
  const headerDescription = computed(() => {
    if (currentSessionName.value) {
      return currentSessionName.value;
    }
    if (hasSession.value) {
      return "未命名会话";
    }
    return "新会话";
  });

  async function scrollToBottom() {
    await nextTick();
    if (messageViewport.value) {
      messageViewport.value.scrollTop = messageViewport.value.scrollHeight;
    }
  }

  async function loadSessions() {
    loadingSessions.value = true;
    try {
      sessions.value = await chatTestService.listSessions();
    } finally {
      loadingSessions.value = false;
    }
  }

  async function loadMessages(userId: string) {
    loadingMessages.value = true;
    try {
      const payload = await chatTestService.getMessages(userId);
      currentUserId.value = userId;
      currentSessionId.value = payload.sessionId;
      messages.value = payload.messages;
      lastIntent.value = "";
      const matched = sessions.value.find((item) => item.userId === userId);
      currentSessionName.value = matched?.name || "";
      await scrollToBottom();
    } finally {
      loadingMessages.value = false;
    }
  }

  async function selectSession(session: ChatTestSessionSummary) {
    await loadMessages(session.userId);
  }

  async function startNewSession() {
    currentUserId.value = buildDraftUserId();
    currentSessionId.value = "";
    currentSessionName.value = "";
    draftInput.value = "";
    lastIntent.value = "";
    messages.value = [];
    await scrollToBottom();
  }

  async function sendMessage() {
    const content = draftInput.value.trim();
    if (!content || sending.value) {
      return;
    }

    messages.value.push({
      role: "user",
      content,
      createdAt: new Date().toISOString(),
    });
    draftInput.value = "";
    sending.value = true;
    await scrollToBottom();

    try {
      const result = await chatTestService.sendMessage(content, currentUserId.value);
      lastIntent.value = result.intent;
      currentSessionId.value = result.sessionId;
      const payload = await chatTestService.getMessages(currentUserId.value);
      messages.value = payload.messages;
      currentSessionId.value = payload.sessionId;
      await scrollToBottom();
    } finally {
      sending.value = false;
    }
  }

  async function saveCurrentSession() {
    if (!currentSessionId.value) {
      ElMessage.warning("请先发送至少一条消息，再保存会话。");
      return;
    }
    const { value } = await ElMessageBox.prompt("给当前会话起个名字，方便后续复查。", "保存会话", {
      confirmButtonText: "保存",
      cancelButtonText: "取消",
      inputValue: currentSessionName.value,
      inputValidator: (input) => input.trim().length > 0,
      inputErrorMessage: "会话名称不能为空",
    });
    await chatTestService.saveSession(currentSessionId.value, value);
    currentSessionName.value = value;
    ElMessage.success("会话已保存");
    await loadSessions();
  }

  async function discardCurrentSession() {
    if (!currentSessionId.value) {
      await startNewSession();
      return;
    }
    await ElMessageBox.confirm("丢弃后当前会话会被关闭，后续不会继续沿用。", "丢弃会话", {
      confirmButtonText: "确认丢弃",
      cancelButtonText: "取消",
      type: "warning",
    });
    await chatTestService.discardSession(currentSessionId.value);
    ElMessage.success("会话已丢弃");
    await loadSessions();
    await startNewSession();
  }

  watch(
    () => messages.value.length,
    async () => {
      await scrollToBottom();
    },
  );

  onMounted(async () => {
    await loadSessions();
  });

  return {
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
  };
}
