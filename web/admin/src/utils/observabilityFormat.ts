/**
 * 数据观察台业务语义翻译与格式化工具函数。
 * 
 * 职责：
 * - 将冷冰冰的原始英文接口事件名、数据来源、修改动作翻译为直观的大白话中文；
 * - 从变更历史 (change_summary) 中提取具体的字段变化细节；
 * - 从 Webhook payload 摘要中提取关联业务的直观语义。
 */

// ── 来源接口映射 ──
const SOURCE_MAP: Record<string, string> = {
  youzan_webhook: "有赞云消息回调接口",
  admin_knowledge: "管理后台配置接口",
  admin_manual: "管理员手动操作",
  seed_knowledge: "种子数据初始化",
};

// ── Webhook 事件类型大白话映射 ──
const EVENT_TYPE_MAP: Record<string, string> = {
  // 商品相关
  item_info: "商品基本信息同步",
  item_state: "商品上下架状态变更",
  item_sku_info: "商品规格(SKU)信息更新",
  youzan_item_skustockorsoldnumupdated: "商品库存与销量变动",
  
  // 交易/订单相关
  trade_order_create: "买家提交订单",
  trade_order_pay: "买家付款完成",
  trade_order_confirm: "卖家确认发货",
  trade_order_success: "订单交易成功",
  trade_order_close: "订单交易关闭",
  trade_order_refund: "退款流程更新",
};

// ── 数据回写动作映射 ──
const ACTION_MAP: Record<string, string> = {
  insert: "新增数据入库",
  update: "修改/更新现有数据",
  delete: "物理删除数据",
  sync: "向量数据库同步",
};

// ── 实体类型映射 ──
const ENTITY_TYPE_MAP: Record<string, string> = {
  product: "商品知识",
  knowledge: "通用知识",
};

/**
 * 翻译数据来源
 */
export function formatSource(source: string): string {
  if (!source) return "系统后台";
  return SOURCE_MAP[source] || source;
}

/**
 * 翻译回写动作
 */
export function formatAction(action: string): string {
  if (!action) return "同步";
  return ACTION_MAP[action.toLowerCase()] || action;
}

/**
 * 翻译 Webhook 事件类型
 */
export function formatEventType(eventType: string): string {
  if (!eventType) return "通用事件推送";
  const lower = eventType.toLowerCase();
  return EVENT_TYPE_MAP[lower] || `事件: ${eventType}`;
}

/**
 * 翻译实体类型
 */
export function formatEntityType(entityType: string): string {
  if (!entityType) return "未知对象";
  return ENTITY_TYPE_MAP[entityType.toLowerCase()] || entityType;
}

/**
 * 解析回写历史 change_summary (即 details)，提取“具体做了什么”
 */
export function parseChangeSummary(details: any, entityType: string): string {
  if (!details || typeof details !== "object") {
    return "同步写入全部数据属性";
  }

  const changes: string[] = [];

  // 判断是否是商品数据变更
  if (entityType?.toLowerCase() === "product" || "price_fen" in details || "stock" in details) {
    if (details.title) {
      changes.push(`商品: ${details.title}`);
    }
    if (details.alias) {
      changes.push(`别名: ${details.alias}`);
    }
    if (details.price_fen !== undefined) {
      changes.push(`价格: ¥${(details.price_fen / 100).toFixed(2)}`);
    }
    if (details.stock !== undefined) {
      changes.push(`库存: ${details.stock} 件`);
    }
    if (details.is_active !== undefined) {
      changes.push(details.is_active ? "标记为「上架在售」" : "标记为「下架停用」");
    }
    if (details.product_write_result) {
      changes.push(`写库: ${details.product_write_result}`);
    }
    if (details.knowledge_write_result) {
      changes.push(`向量同步: ${details.knowledge_write_result}`);
    }
  } 
  // 知识库数据变更
  else {
    if (details.title) {
      changes.push(`知识条目: ${details.title}`);
    }
    if (details.category) {
      changes.push(`分类: ${details.category}`);
    }
    if (details.is_active !== undefined) {
      changes.push(details.is_active ? "状态: 启用" : "状态: 禁用");
    }
    if (details.priority !== undefined) {
      changes.push(`优先级: ${details.priority}`);
    }
  }

  return changes.length > 0 ? changes.join(" | ") : "全量覆盖数据属性";
}

/**
 * 解析 Webhook payload_summary 并提炼业务关联详情
 */
export function parseWebhookSummary(details: any, eventType: string, businessType: string, businessKey: string): string {
  const typeLower = eventType?.toLowerCase() || "";
  const bizTypeLower = businessType?.toLowerCase() || "";

  if (bizTypeLower === "trade" || typeLower.startsWith("trade_")) {
    return `订单协同 ── 关联单号: ${businessKey || details.id || "-"}`;
  }

  if (bizTypeLower === "item" || typeLower.startsWith("item_") || typeLower.includes("skustock")) {
    return `商品联动 ── 关联商品 ID: ${businessKey || "-"}`;
  }

  if (bizTypeLower === "chat") {
    return `在线咨询 ── 关联顾客 ID: ${businessKey || details.buyer_id || "-"}`;
  }

  return `其他业务 ── 标识: ${businessKey || "-"}`;
}
