export interface ChatTestSessionSummary {
  id: string;
  name: string;
  userId: string;
  msgCount: number;
  createdAt: string;
}

export interface ChatTestMessage {
  role: string;
  content: string;
  createdAt: string;
}

export interface ChatTestSendResult {
  reply: string;
  intent: string;
  sessionId: string;
}
