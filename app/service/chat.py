"""
核心对话循环。

所有渠道的消息最终汇聚到此模块处理：
1. 保存用户消息
2. 判断会话状态（AI 服务 / 人工服务）
3. 构建上下文 + 调用 DeepSeek
4. 处理 LLM 返回（文本回复 / Function Calling）
5. 循环最多 3 轮 tool call
"""

import json

from app.exceptions import LLMError
from app.logger import setup_logger
from app.models.knowledge import KnowledgeEntry
from app.models.message import Message, MessageRole
from app.models.session import Session, SessionCreate, SessionStatus
from app.repository.message_repo import MessageRepo
from app.repository.session_repo import SessionRepo
from app.repository.transfer_repo import TransferRepo
from app.service.knowledge_retriever import KnowledgeRetriever
from app.service.llm.client import chat_completion as llm_chat
from app.service.llm.functions import FUNCTION_DEFINITIONS, MAX_TOOL_ROUNDS, dispatch_tool
from app.service.llm.intent import IntentType, detect_intent
from app.service.llm.intent_taxonomy import is_transfer_intent
from app.service.llm.prompt import build_system_prompt
from app.service.llm.query_rewriter import rewrite_query
from app.service.llm.soothe import apply_soothe, needs_soothe
from app.service.session_manager import SessionManager
from app.service.transfer_manager import TransferManager

logger = setup_logger()

# ── 业务常量 ──────────────────────────────────────────────────────────────────
FALLBACK_REPLY = "系统正忙，请稍后再试或联系人工客服。"
TRANSFER_REPLY = "非常抱歉给您带来不好的体验，已为您转接人工客服，请稍候~"
DEFAULT_SEARCH_QUERY = "芸熙烘焙 产品 价格"
KNOWLEDGE_SEARCH_LIMIT = 8
INTENT_HISTORY_MESSAGES = 4
INTENT_CONTENT_PREVIEW = 80
TRANSFER_SUMMARY_LENGTH = 200
QUERY_TIMEOUT_REPLY = "正在为您查询，请稍候。如果长时间没有回复，请联系人工客服。"


class ChatService:
    """AI 对话服务：处理消息、调用 LLM、管理工具调用循环。"""

    def __init__(
        self,
        session_repo: SessionRepo,
        message_repo: MessageRepo,
        transfer_repo: TransferRepo,
        knowledge_retriever: KnowledgeRetriever,
    ) -> None:
        self._session_mgr = SessionManager(session_repo, message_repo)
        self._session_repo = session_repo
        self._message_repo = message_repo
        self._transfer_mgr = TransferManager(transfer_repo)
        self._knowledge = knowledge_retriever

    async def handle_message_and_reply_youzan(self, buyer_id: str, content: str, msg_id: str) -> None:
        """处理消息，并将 AI 回复通过有赞客户端投递给买家（业务层闭环封装）。"""
        reply = await self.handle_message(
            channel="youzan",
            user_id=buyer_id,
            content=content,
            channel_msg_id=msg_id,
        )
        if reply:
            from app.repository.config_repo import ConfigRepo
            from app.service.youzan.client import YouzanClient
            yz_client = YouzanClient(config_repo=ConfigRepo(self._session_repo._db))
            await yz_client.send_reply(buyer_open_id=buyer_id, content=reply)
            await yz_client.close()

    async def handle_message(
        self,
        channel: str,
        user_id: str,
        content: str,
        staff_id: str = "",
        channel_msg_id: str = "",
    ) -> str | None:
        """
        处理用户消息的主入口。

        参数：
            channel: 渠道标识（youzan / wecom_1on1 / wecom_group）
            user_id: 渠道用户 ID
            content: 消息内容
            staff_id: 所属员工 ID（企微必传）
            channel_msg_id: 渠道原始消息 ID（用于去重）
        返回：
            回复文本，无需回复时返回 None
        """
        # 1. 幂等去重
        if channel_msg_id and await self._message_repo.exists(channel_msg_id):
            logger.debug("消息已处理，跳过: %s", channel_msg_id)
            return None

        # 2. 获取或创建会话
        session = await self._session_repo.get_or_create(
            SessionCreate(id="", channel=channel, user_id=user_id, staff_id=staff_id),
        )

        # 3. 保存用户消息
        user_msg = Message(
            id="", session_id=session.id, role=MessageRole.USER,
            content=content, channel_msg_id=channel_msg_id,
        )
        await self._message_repo.save(user_msg)

        # 4. 状态判断：人工服务中则不调用 LLM
        if session.status in (SessionStatus.TRANSFER_PENDING, SessionStatus.HUMAN_SERVICE):
            logger.info("会话 %s 处于人工服务状态，跳过 AI", session.id)
            return None

        # 5. 意图识别（决定走售后、知识搜索还是闲聊）
        history = await self._session_mgr.build_context(session.id)
        history_text = "\n".join(
            f"{'用户' if m.get('role') == 'user' else 'AI'}：{m.get('content', '')[:INTENT_CONTENT_PREVIEW]}"
            for m in history[-INTENT_HISTORY_MESSAGES:] if m.get("role") in ("user", "assistant")
        )
        intent = await detect_intent(content, history=history_text)
        logger.info("会话 %s 意图: %s", session.id, intent.name)

        # 转人工 → 自动创建转人工工单
        if is_transfer_intent(intent):
            try:
                await self._transfer_mgr.request_transfer(
                    session.id, user_id, reason=content,
                    summary=history_text[-TRANSFER_SUMMARY_LENGTH:],
                )
                await self._session_repo.update_status(session.id, SessionStatus.TRANSFER_PENDING)
            except Exception as exc:
                logger.error("创建售后转人工工单失败: session=%s err=%s", session.id, exc)
                return FALLBACK_REPLY
            assistant_msg = Message(
                id="", session_id=session.id, role=MessageRole.ASSISTANT,
                content=TRANSFER_REPLY,
            )
            await self._message_repo.save(assistant_msg)
            return TRANSFER_REPLY

        # 7. 进入 AI 对话循环
        reply = await self._ai_conversation_loop(session, user_query=content, intent=intent)

        # 清理 Markdown 符号（LLM 偶尔会输出 ** 加粗）
        if reply:
            reply = reply.replace("**", "").replace("*", "").replace("__", "")

        # 安抚策略：检测到敏感词时附加道歉前缀
        if reply and needs_soothe(content):
            reply = apply_soothe(reply)

        # 8. 保存 AI 回复
        if reply:
            assistant_msg = Message(
                id="", session_id=session.id, role=MessageRole.ASSISTANT,
                content=reply,
            )
            await self._message_repo.save(assistant_msg)

        return reply

    async def _load_knowledge_entries(
        self,
        user_query: str,
        history_text: str,
        intent: IntentType,
    ) -> list[KnowledgeEntry]:
        if intent == IntentType.SMALL_TALK:
            return await self._knowledge.search_keyword_only(user_query, limit=KNOWLEDGE_SEARCH_LIMIT)

        search_query = user_query or DEFAULT_SEARCH_QUERY
        rewritten = await rewrite_query(search_query, history=history_text)
        try:
            return await self._knowledge.search(rewritten, limit=KNOWLEDGE_SEARCH_LIMIT)
        except Exception as exc:
            logger.error("知识库检索失败，使用空上下文继续: %s", exc)
            return []

    async def _ai_conversation_loop(
        self, session: Session, user_query: str = "", intent: IntentType = IntentType.PRODUCT_CONSULTATION,
    ) -> str | None:
        """
        AI 对话循环（最多 MAX_TOOL_ROUNDS 轮工具调用）。

        流程：
        1. 构建上下文（系统提示 + 历史消息）
        2. 调用 DeepSeek
        3. 处理响应：
           - stop → 直接回复
           - tool_calls → 执行工具，继续循环
           - 超过最大轮数 → 兜底回复
        """
        # 根据意图调整检索策略
        history = await self._session_mgr.build_context(session.id)
        history_text = "\n".join(
            f"{'用户' if m.get('role')=='user' else 'AI'}：{m.get('content','')[:INTENT_CONTENT_PREVIEW]}"
            for m in history[-INTENT_HISTORY_MESSAGES:] if m.get("role") in ("user", "assistant")
        )
        knowledge_entries = await self._load_knowledge_entries(user_query, history_text, intent)

        messages: list[dict] = [
            {"role": "system", "content": build_system_prompt(knowledge_entries)},
        ]

        history = await self._session_mgr.build_context(session.id)
        messages.extend(history)

        tool_round = 0

        while tool_round <= MAX_TOOL_ROUNDS:
            try:
                raw = await llm_chat(messages, tools=FUNCTION_DEFINITIONS)
                response = json.loads(raw)
                choice = response["choices"][0]
                msg = choice["message"]
            except LLMError:
                logger.error("LLM 调用失败，返回兜底回复")
                return FALLBACK_REPLY
            except (json.JSONDecodeError, KeyError, IndexError) as exc:
                logger.error("LLM 响应解析失败，返回兜底回复: %s", exc)
                return FALLBACK_REPLY

            finish_reason = choice.get("finish_reason", "stop")

            if finish_reason == "stop":
                # LLM 返回纯文本，直接回复
                return msg.get("content", "")

            if finish_reason == "tool_calls" and tool_round < MAX_TOOL_ROUNDS:
                # LLM 请求调用工具
                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError as exc:
                        logger.error("工具参数解析失败，跳过: tool=%s err=%s", fn_name, exc)
                        fn_args = {}

                    logger.info("工具调用: %s args=%s", fn_name, fn_args)

                    # transfer_to_human 需要 TransferManager 依赖，在此拦截
                    if fn_name == "transfer_to_human":
                        reason = fn_args.get("reason", "用户通过工具请求转人工")
                        try:
                            await self._transfer_mgr.request_transfer(
                                session.id, session.user_id, reason=reason,
                                summary=history_text[-TRANSFER_SUMMARY_LENGTH:],
                            )
                            await self._session_repo.update_status(session.id, SessionStatus.TRANSFER_PENDING)
                            result = json.dumps({"status": "success", "message": "已为您转接人工客服，请稍候"}, ensure_ascii=False)
                        except Exception as exc:
                            logger.error("创建转人工工单失败: session=%s err=%s", session.id, exc)
                            result = json.dumps({"status": "error", "message": "转接失败，请稍后重试"}, ensure_ascii=False)
                    else:
                        result = await dispatch_tool(fn_name, fn_args, session, self._knowledge)

                    # 将 tool call 和结果追加到消息列表
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": fn_name, "arguments": json.dumps(fn_args, ensure_ascii=False)},
                        }],
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

                tool_round += 1
                continue

            # 超限或未知 finish_reason
            break

        return QUERY_TIMEOUT_REPLY

    async def handle_human_reply(self, session_id: str, content: str) -> None:
        """
        人工客服回复消息。

        参数：
            session_id: 会话 ID
            content: 回复内容
        """
        msg = Message(
            id="", session_id=session_id, role=MessageRole.ASSISTANT,
            content=content,
        )
        await self._message_repo.save(msg)
        logger.info("人工客服回复: session=%s", session_id)

    async def handle_youzan_system_event(self, payload: dict, updated_at_str: str, msg_id: str) -> None:
        """
        处理有赞推送的系统事件（商品变动、交易订单变动等，属于 service 业务层）。
        向右合流物理宽表，向左合流 RAG 增量知识库，并部署四大分析埋点触点。
        """
        from app.repository.youzan_repo import YouzanProductRepo, YouzanOrderRepo
        from app.repository.analytics_repo import AnalyticsRepo
        from app.repository.knowledge_repo import KnowledgeRepo
        from app.service.youzan.client import YouzanClient
        from app.repository.config_repo import ConfigRepo
        from app.config import settings
        import datetime
        import urllib.parse
        import json
        import asyncio

        db = self._session_repo._db
        event_type = payload.get("type", "")

        msg_str = urllib.parse.unquote(payload.get("msg", "{}"))
        try:
            msg_obj = json.loads(msg_str)
        except Exception as exc:
            logger.error("解析有赞系统事件 msg 详情失败: %s", exc)
            return

        product_repo = YouzanProductRepo(db)
        order_repo = YouzanOrderRepo(db)
        analytics_repo = AnalyticsRepo(db)
        knowledge_repo = KnowledgeRepo(db)

        # --- 触点二/四：交易生命周期流转与 24小时 ROI AI导购支付归因 ---
        if event_type.startswith("trade_"):
            tid = msg_obj.get("tid", "")
            if not tid:
                logger.warning("有赞交易事件缺少 tid")
                return

            logger.info("开始处理有赞交易 Webhook 事件 [%s]: tid=%s", event_type, tid)
            try:
                # (1) 读取本地已有状态
                old_status = "NONE"
                local_order = await order_repo.get_by_order_no(tid)
                if local_order:
                    old_status = local_order["status"]

                # (2) 现场秒级拉取有赞最新数据，保障最终一致性（死锁脑裂）
                yz_client = YouzanClient(config_repo=ConfigRepo(db))
                raw_order = await yz_client.get_order(tid)
                await yz_client.close()

                outer_data = raw_order.get("data") or raw_order.get("response") if isinstance(raw_order, dict) else None
                if isinstance(outer_data, dict) and "trade" in outer_data:
                    trade = outer_data["trade"]
                    status = trade.get("status", "WAIT_BUYER_PAY")
                    payment_fen = int(float(trade.get("payment", 0)) * 100)
                    buyer_id = trade.get("buyer_id", "") or trade.get("open_id", "")

                    # 结构化抽取并拼接商品描述
                    order_items = trade.get("orders", [])
                    titles_list = []
                    total_qty = 0
                    for item in order_items:
                        title = item.get("title", "商品")
                        num = item.get("num", 1)
                        titles_list.append(f"{title} x {num}")
                        total_qty += num
                    product_titles = ", ".join(titles_list)
                    created = trade.get("created", "")

                    # (3) 向右分流：原子 Upsert 保存至 orders 物理大宽表（带乐观时序锁）
                    await order_repo.upsert_order(
                        order_no=tid,
                        buyer_id=buyer_id,
                        status=status,
                        amount_fen=payment_fen,
                        logistics_no=local_order["logistics_no"] if local_order else "",
                        logistics_status=local_order["logistics_status"] if local_order else "",
                        product_titles=product_titles,
                        total_quantity=total_qty,
                        created_at=created,
                        updated_at=updated_at_str
                    )

                    # (4) 触点二：记录履约订单生命周期状态变更埋点 (order_state_change)
                    if old_status != status:
                        await analytics_repo.add_event(
                            session_id=None,
                            buyer_id=buyer_id,
                            event_type="order_state_change",
                            event_source="webhook_youzan",
                            ref_id=tid,
                            meta_data=json.dumps({"old_status": old_status, "new_status": status}, ensure_ascii=False),
                            created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        logger.info("已成功记录订单履约时效埋点: tid=%s, old=%s, new=%s", tid, old_status, status)

                    # (5) 触点四：AI 导购付款成功归因埋点 (order_conversion)
                    # 在付款成功的事件状态（由 WAIT_BUYER_PAY 流转到 WAIT_SELLER_SEND_GOODS 或直接付款成功）进行 lookback
                    if event_type == "trade_TradeBuyerPay" or (old_status in ("NONE", "WAIT_BUYER_PAY") and status in ("WAIT_SELLER_SEND_GOODS", "TRADE_PAID", "TRADE_SUCCESS")):
                        logger.info("触发 24 小时 AI 导购业绩付款归因校验: buyer=%s", buyer_id)
                        for item in order_items:
                            item_id = item.get("item_id", 0)
                            if item_id:
                                product = await product_repo.get_by_id(item_id)
                                if product:
                                    alias = product["alias"]
                                    # 回溯 24 小时推荐行为
                                    ai_session_id = await analytics_repo.check_ai_recommend_for_conversion(buyer_id, alias, lookback_hours=24)
                                    if ai_session_id:
                                        # ROI 归因命中，记录业绩埋点日志供 Dashboard 画布展现
                                        await analytics_repo.add_event(
                                            session_id=ai_session_id,
                                            buyer_id=buyer_id,
                                            event_type="order_conversion",
                                            event_source="webhook_youzan",
                                            ref_id=tid,
                                            meta_data=json.dumps({
                                                "product_title": item.get("title", ""),
                                                "product_alias": alias,
                                                "amount_fen": int(float(item.get("payment", 0)) * 100),
                                                "lookback": "24_hours"
                                            }, ensure_ascii=False),
                                            created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        )
                                        logger.info("🎉 完美！AI 导购业绩归因匹配成功！已为 Dashboard 记账绩效: session_id=%s, buyer_id=%s, gmv_fen=%s", ai_session_id, buyer_id, item.get("payment"))
            except Exception as exc:
                logger.error("处理有赞交易系统事件失败: tid=%s err=%s", tid, exc)

        # --- 触点一：商品属性上下架/更新（双轨分流 + price_sync / stock_alert 审计埋点） ---
        elif event_type.startswith("item_") or event_type == "ITEM_STATE":
            item_id = msg_obj.get("item_id", 0)
            if not item_id:
                logger.warning("有赞商品事件缺少 item_id")
                return

            logger.info("开始处理有赞商品 Webhook 事件 [%s]: item_id=%s", event_type, item_id)
            try:
                # (1) 读取本地已有属性用以对比
                old_price = -1
                old_stock = -1
                local_product = await product_repo.get_by_id(item_id)
                if local_product:
                    old_price = local_product["price_fen"]
                    old_stock = local_product["stock"]

                # (2) 现场拉取有赞商品实况
                yz_client = YouzanClient(config_repo=ConfigRepo(db))
                raw_product = await yz_client.get_product(item_id)
                await yz_client.close()

                outer_data = raw_product.get("data") or raw_product.get("response") if isinstance(raw_product, dict) else None
                if isinstance(outer_data, dict) and "item" in outer_data:
                    item_data = outer_data["item"]
                    title = item_data.get("title", "")
                    alias = item_data.get("alias", "")
                    price_fen = item_data.get("price", 0)
                    stock = item_data.get("quantity", 0)
                    image = item_data.get("pic_url") or item_data.get("image") or ""

                    # 商品上架在售状态判定
                    is_active = 1
                    if "instock" in event_type or event_type.endswith("Instock"):
                        is_active = 0  # 软下架入库

                    # 提取多规格 SKU 数据及详情页描述
                    skus = item_data.get("skus", [])
                    skus_json = json.dumps(skus, ensure_ascii=False)

                    raw_desc = item_data.get("desc", "") or item_data.get("summary", "") or ""
                    import re
                    # 剥除有赞 HTML 标签，保留高密度的原料、奶油与夹心纯文本介绍
                    desc_clean = re.sub(r"<.*?>", "", raw_desc)
                    desc_clean = re.sub(r"\s+", " ", desc_clean)
                    desc_clean = re.sub(r"\n+", "\n", desc_clean).strip()

                    # 智能解析 SKU properties 抽取奶油/尺寸/规格/夹心等高级标签属性
                    spec_names = []
                    for sku in skus:
                        prop_json = sku.get("properties_name_json", "")
                        if prop_json:
                            try:
                                props = json.loads(prop_json)
                                for p in props:
                                    v_val = p.get("v", "")
                                    if v_val:
                                        spec_names.append(v_val)
                            except:
                                pass

                    # 补充详情页里的关键成分与特征标签（如蜜红豆、抹茶、草莓、夹心等）
                    special_ingredients = ["蜜红豆", "抹茶", "草莓", "芒果", "提拉米苏", "巧克力", "动物奶油", "夹心", "千层", "乳酪", "芝士", "冷藏", "保质期"]
                    found_ingredients = [ing for ing in special_ingredients if ing in desc_clean or ing in title]

                    status_lbl = "在售" if is_active == 1 else "下架"
                    tags_list = [status_lbl]
                    if spec_names:
                        tags_list.extend(list(set(spec_names)))
                    if found_ingredients:
                        tags_list.extend(list(set(found_ingredients)))
                    tags_str = ", ".join(tags_list)

                    # (3) 向右分流：原子 Upsert 保存至 youzan_products 物理商品大宽表
                    await product_repo.upsert_product(
                        item_id=item_id,
                        title=title,
                        alias=alias,
                        price_fen=price_fen,
                        stock=stock,
                        image=image,
                        is_active=is_active,
                        updated_at=updated_at_str,
                        skus_json=skus_json,
                        desc=desc_clean,
                        tags=tags_str,
                    )

                    # (4) 向左分流：原子增量更新 RAG（完全取代本地老旧静态商品文件）
                    sku_list_str = []
                    for sku in skus:
                        price_yuan = sku.get("price", price_fen) / 100.0
                        qty = sku.get("quantity", 0)
                        prop_json = sku.get("properties_name_json", "")
                        prop_desc = "标准规格"
                        if prop_json:
                            try:
                                props = json.loads(prop_json)
                                prop_desc = " | ".join([f"{p.get('k')}:{p.get('v')}" for p in props])
                            except:
                                pass
                        sku_list_str.append(f"- 规格型号【{prop_desc}】：售价 ￥{price_yuan:.2f} 元，当前可用库存 {qty} 件")
                    skus_text = "\n".join(sku_list_str) if sku_list_str else f"- 规格：单售价 ￥{price_fen/100.0:.2f} 元，当前可用总库存 {stock} 件"

                    detail_url = f"https://h5.youzan.com/v2/showcase/goods?alias={alias}"
                    content_md = (
                        f"商品名称：{title}\n"
                        f"在售状态：{status_lbl}\n"
                        f"商品规格及秒级实时库存明细：\n{skus_text}\n"
                        f"商品特征与配方属性标签：{tags_str}\n"
                        f"直购下单链接：{detail_url}\n"
                        f"原料配方、保质期及夹心介绍：\n{desc_clean or '精品烘焙推荐，新西兰进口动物奶油调配，不含防腐剂。建议0-4℃冷藏并于3天内食用完毕。'}"
                    )

                    if is_active == 1:
                        # SQLite RAG 商品知识落库
                        await knowledge_repo.upsert_product_knowledge(
                            youzan_item_id=str(item_id),
                            title=title,
                            content=content_md,
                            keywords=f"商品, 价格, 推荐, 蛋糕, {title}, {tags_str}",
                            priority=50,
                            updated_at=updated_at_str
                        )
                        # 增量计算 1 个 Embedding 并原地追加/替换向量
                        vs = self._knowledge._vs
                        if vs:
                            vector = vs._get_model().encode([f"{title} {content_md}"], normalize_embeddings=True)[0].tolist()
                            vs.upsert_one(title, vector)
                            # 内存脏页写缓冲原子落盘落库，阻断写放大
                            await asyncio.to_thread(vs.save, settings.EMBEDDING_PATH)
                    else:
                        # RAG 下架物理擦除
                        await knowledge_repo.delete_product_knowledge(str(item_id))
                        vs = self._knowledge._vs
                        if vs:
                            vs.delete_one(title)
                            await asyncio.to_thread(vs.save, settings.EMBEDDING_PATH)

                    # (5) 触点一：价格/库存异动审计变更埋点 (price_sync / stock_alert)
                    if old_price != -1 and old_price != price_fen:
                        await analytics_repo.add_event(
                            session_id=None,
                            buyer_id=None,
                            event_type="price_sync",
                            event_source="webhook_youzan",
                            ref_id=str(item_id),
                            meta_data=json.dumps({"product_title": title, "old_price_fen": old_price, "new_price_fen": price_fen}, ensure_ascii=False),
                            created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        logger.info("已成功记录商品价格调价审计埋点: title=%s, old=%d, new=%d", title, old_price, price_fen)

                    if old_stock != -1 and old_stock != stock:
                        await analytics_repo.add_event(
                            session_id=None,
                            buyer_id=None,
                            event_type="stock_alert",
                            event_source="webhook_youzan",
                            ref_id=str(item_id),
                            meta_data=json.dumps({"product_title": title, "old_stock": old_stock, "new_stock": stock}, ensure_ascii=False),
                            created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        logger.info("已成功记录商品库存预警审计埋点: title=%s, old_stock=%d, new_stock=%d", title, old_stock, stock)

            except Exception as exc:
                logger.error("处理有赞商品系统事件失败: item_id=%s err=%s", item_id, exc)

