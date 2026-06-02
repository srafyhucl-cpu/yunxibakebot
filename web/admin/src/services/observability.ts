import http from "./http";

import type {
  ObservabilityCurrentItem,
  ObservabilityCurrentPayload,
  ObservabilityDetailField,
  ObservabilityHistoryItem,
  ObservabilityHistoryPayload,
  ObservabilityWebhookItem,
  ObservabilityWebhookPayload,
} from "@/types/observability";

interface CurrentResponse {
  code: number;
  total: number;
  data: Array<{
    entity_type: string;
    entity_key: string;
    title: string;
    subtitle: string;
    category: string;
    status_text: string;
    is_active: boolean;
    updated_at: string;
    last_sync_source: string;
    last_sync_ref: string;
    summary: string[];
    details: Array<{
      label: string;
      value: string;
    }>;
  }>;
}

interface HistoryResponse {
  code: number;
  total?: number;
  data: Array<{
    id: number;
    entity_type: string;
    entity_key: string;
    category: string;
    title: string;
    source: string;
    source_ref: string;
    session_id: string;
    webhook_msg_id: string;
    webhook_event_type?: string;
    action: string;
    status: string;
    error_type: string;
    error_message: string;
    occurred_at: string;
    summary_lines: string[];
    details: Record<string, unknown>;
  }>;
}

interface HistoryDetailResponse {
  code: number;
  data: HistoryResponse["data"][number];
}

interface WebhookResponse {
  code: number;
  total?: number;
  data: Array<{
    id: number;
    msg_id: string;
    event_type: string;
    business_type: string;
    business_key: string;
    status: string;
    process_stage: string;
    error_type: string;
    error_message: string;
    received_at: string;
    duration_ms: number;
    summary_lines: string[];
    details: Record<string, unknown>;
  }>;
}

interface WebhookDetailResponse {
  code: number;
  data: WebhookResponse["data"][number];
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function normalizeDetailFields(details: unknown): ObservabilityDetailField[] {
  if (!details || typeof details !== "object" || Array.isArray(details)) {
    return [{ label: "原始内容", value: stringifyValue(details) }];
  }
  
  const d = details as Record<string, unknown>;
  const highlightKeys = new Set<string>();
  
  if (d.old_price_fen !== undefined) {
    highlightKeys.add("old_price_fen");
    highlightKeys.add("price_fen");
  }
  if (d.old_stock !== undefined) {
    highlightKeys.add("old_stock");
    highlightKeys.add("stock");
  }

  return Object.entries(d).map(([label, value]) => ({
    label,
    value: stringifyValue(value),
    highlight: highlightKeys.has(label),
  }));
}

function normalizeCurrentItem(item: CurrentResponse["data"][number]): ObservabilityCurrentItem {
  return {
    entityType: item.entity_type,
    entityKey: item.entity_key,
    title: item.title,
    subtitle: item.subtitle || "",
    category: item.category || "",
    statusText: item.status_text || "",
    isActive: item.is_active,
    updatedAt: item.updated_at || "",
    lastSyncSource: item.last_sync_source || "",
    lastSyncRef: item.last_sync_ref || "",
    summary: item.summary || [],
    details: item.details || [],
  };
}

function normalizeHistoryItem(item: HistoryResponse["data"][number]): ObservabilityHistoryItem {
  return {
    id: item.id,
    entityType: item.entity_type,
    entityKey: item.entity_key,
    category: item.category || "",
    title: item.title,
    source: item.source || "",
    sourceRef: item.source_ref || "",
    sessionId: item.session_id || "",
    webhookMsgId: item.webhook_msg_id || "",
    webhookEventType: item.webhook_event_type || "",
    action: item.action || "",
    status: item.status || "",
    errorType: item.error_type || "",
    errorMessage: item.error_message || "",
    occurredAt: item.occurred_at || "",
    summaryLines: item.summary_lines || [],
    detailFields: normalizeDetailFields(item.details),
    details: item.details || {},
  };
}

function normalizeWebhookItem(item: WebhookResponse["data"][number]): ObservabilityWebhookItem {
  return {
    id: item.id,
    msgId: item.msg_id || "",
    eventType: item.event_type || "",
    businessType: item.business_type || "",
    businessKey: item.business_key || "",
    status: item.status || "",
    processStage: item.process_stage || "",
    errorType: item.error_type || "",
    errorMessage: item.error_message || "",
    receivedAt: item.received_at || "",
    durationMs: item.duration_ms || 0,
    summaryLines: item.summary_lines || [],
    detailFields: normalizeDetailFields(item.details),
  };
}

export const observabilityService = {
  async listCurrent(params: {
    page: number;
    view: string;
    category: string;
    keyword: string;
    productStatus: string;
  }): Promise<ObservabilityCurrentPayload> {
    const response = await http.get<CurrentResponse>("/observability/current", {
      params: {
        page: params.page,
        view: params.view,
        category: params.category,
        keyword: params.keyword,
        product_status: params.productStatus,
      },
    });
    return {
      items: response.data.data.map(normalizeCurrentItem),
      total: response.data.total,
    };
  },

  async listHistory(params: {
    page: number;
    source: string;
    status: string;
    entityType: string;
    keyword: string;
  }): Promise<ObservabilityHistoryPayload> {
    const response = await http.get<HistoryResponse>("/observability/history", {
      params: {
        page: params.page,
        source: params.source,
        status: params.status,
        entity_type: params.entityType,
        keyword: params.keyword,
      },
    });
    return {
      items: response.data.data.map(normalizeHistoryItem),
      total: response.data.total || 0,
    };
  },

  async getHistoryDetail(entryId: number): Promise<ObservabilityHistoryItem> {
    const response = await http.get<HistoryDetailResponse>(`/observability/history/${entryId}`);
    return normalizeHistoryItem(response.data.data);
  },

  async listWebhooks(params: {
    page: number;
    status: string;
    eventType: string;
    keyword: string;
  }): Promise<ObservabilityWebhookPayload> {
    const response = await http.get<WebhookResponse>("/observability/webhooks", {
      params: {
        page: params.page,
        status: params.status,
        event_type: params.eventType,
        keyword: params.keyword,
      },
    });
    return {
      items: response.data.data.map(normalizeWebhookItem),
      total: response.data.total || 0,
    };
  },

  async getWebhookDetail(eventId: number): Promise<ObservabilityWebhookItem> {
    const response = await http.get<WebhookDetailResponse>(`/observability/webhooks/${eventId}`);
    return normalizeWebhookItem(response.data.data);
  },
};
