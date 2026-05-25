import http from "./http";

import type {
  ChatTestMessage,
  ChatTestSendResult,
  ChatTestSessionSummary,
} from "@/types/chatTest";

interface ListSessionsResponse {
  code: number;
  data: Array<{
    id: string;
    name: string;
    user_id: string;
    msg_count: number;
    created_at: string;
  }>;
}

interface ChatHistoryResponse {
  code: number;
  session_id?: string;
  data: Array<{
    role: string;
    content: string;
    created_at: string;
  }>;
}

interface SendMessageResponse {
  code: number;
  reply: string;
  intent: string;
  session_id: string;
}

export const chatTestService = {
  async listSessions(): Promise<ChatTestSessionSummary[]> {
    const response = await http.get<ListSessionsResponse>("/chat-test/sessions");
    return response.data.data.map((item) => ({
      id: item.id,
      name: item.name,
      userId: item.user_id,
      msgCount: item.msg_count,
      createdAt: item.created_at,
    }));
  },

  async getMessages(userId: string): Promise<{ sessionId: string; messages: ChatTestMessage[] }> {
    const response = await http.get<ChatHistoryResponse>("/chat-test/messages", {
      params: { user_id: userId },
    });
    return {
      sessionId: response.data.session_id || "",
      messages: response.data.data.map((item) => ({
        role: item.role,
        content: item.content,
        createdAt: item.created_at,
      })),
    };
  },

  async sendMessage(content: string, userId: string): Promise<ChatTestSendResult> {
    const response = await http.post<SendMessageResponse>("/chat-test", {
      content,
      user_id: userId,
    });
    return {
      reply: response.data.reply,
      intent: response.data.intent,
      sessionId: response.data.session_id,
    };
  },

  async saveSession(sessionId: string, name: string): Promise<void> {
    await http.post("/chat-test/save", {
      session_id: sessionId,
      name,
    });
  },

  async discardSession(sessionId: string): Promise<void> {
    await http.delete(`/chat-test/session/${sessionId}`);
  },
};
