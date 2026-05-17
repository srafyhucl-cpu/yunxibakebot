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
from app.models.message import Message, MessageRole
from app.models.session import Session, SessionCreate
from app.repository.message_repo import MessageRepo
from app.repository.session_repo import SessionRepo
from app.repository.transfer_repo import TransferRepo
from app.service.knowledge_retriever import KnowledgeRetriever
from app.service.llm.client import chat_completion as llm_chat
from app.service.llm.functions import FUNCTION_DEFINITIONS, MAX_TOOL_ROUNDS, dispatch_tool
from app.service.llm.prompt import build_system_prompt
from app.service.session_manager import SessionManager
from app.service.transfer_manager import TransferManager

logger = setup_logger()

# 兜底回复：LLM 调用失败时回复用户
FALLBACK_REPLY = "系统正忙，请稍后再试或联系人工客服。"


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
        if session.status in ("transfer_pending", "human_service"):
            logger.info("会话 %s 处于人工服务状态，跳过 AI", session.id)
            return None

        # 5. 进入 AI 对话循环（传入用户消息作为知识搜索关键词）
        reply = await self._ai_conversation_loop(session, user_query=content)

        # 6. 保存 AI 回复
        if reply:
            assistant_msg = Message(
                id="", session_id=session.id, role=MessageRole.ASSISTANT,
                content=reply,
            )
            await self._message_repo.save(assistant_msg)

        return reply

    async def _ai_conversation_loop(self, session: Session, user_query: str = "") -> str | None:
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
        # 根据用户提问检索相关知识
        search_query = user_query or "芸熙烘焙 产品 价格"
        knowledge_entries = await self._knowledge.search(search_query, limit=8)

        messages: list[dict] = [
            {"role": "system", "content": build_system_prompt(knowledge_entries)},
        ]

        history = await self._session_mgr.build_context(session.id)
        messages.extend(history)

        tool_round = 0

        while tool_round <= MAX_TOOL_ROUNDS:
            try:
                raw = await llm_chat(messages, tools=FUNCTION_DEFINITIONS)
            except LLMError:
                logger.error("LLM 调用失败，返回兜底回复")
                return FALLBACK_REPLY

            response = json.loads(raw)
            choice = response["choices"][0]
            msg = choice["message"]

            finish_reason = choice.get("finish_reason", "stop")

            if finish_reason == "stop":
                # LLM 返回纯文本，直接回复
                return msg.get("content", "")

            if finish_reason == "tool_calls" and tool_round < MAX_TOOL_ROUNDS:
                # LLM 请求调用工具
                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    fn_name = tc["function"]["name"]
                    fn_args = json.loads(tc["function"]["arguments"])

                    logger.info("工具调用: %s args=%s", fn_name, fn_args)

                    # 执行工具
                    result = await dispatch_tool(fn_name, fn_args, session)

                    # 将 tool call 和结果追加到消息列表
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": fn_name, "arguments": tc["function"]["arguments"]},
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

        return "正在为您查询，请稍候。如果长时间没有回复，请联系人工客服。"

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
