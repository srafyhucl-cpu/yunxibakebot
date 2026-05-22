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
from app.service.llm.intent_types import is_transfer_intent
from app.service.llm.prompt import build_system_prompt
from app.service.llm.query_rewriter import rewrite_query
from app.service.llm.soothe import apply_soothe, needs_soothe
from app.service.session_manager import SessionManager
from app.service.transfer_manager import TransferManager
from app.repository.config_repo import ConfigRepo
from app.service.youzan.client import YouzanClient
from app.service.youzan.event_handler import YouzanEventHandler

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
        self._youzan_client = YouzanClient(config_repo=ConfigRepo(session_repo._db))
        self._youzan_events = YouzanEventHandler(
            db=session_repo._db,
            knowledge_retriever=knowledge_retriever,
            youzan_client=self._youzan_client,
        )

    async def handle_message_and_reply_youzan(self, buyer_id: str, content: str, msg_id: str) -> None:
        """处理消息，并将 AI 回复通过有赞客户端投递给买家（业务层闭环封装）。"""
        reply = await self.handle_message(
            channel="youzan",
            user_id=buyer_id,
            content=content,
            channel_msg_id=msg_id,
        )
        if reply:
            await self._youzan_client.send_reply(buyer_open_id=buyer_id, content=reply)

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
        """有赞系统事件处理（商品/交易 Webhook），委托至 YouzanEventHandler。"""
        await self._youzan_events.handle_system_event(payload, updated_at_str, msg_id)

