"""
有赞系统事件分发器。

接收来自 ChatService 的有赞 Webhook 系统事件，解析 msg 字段后
按事件类型分发至 event_trade / event_item 专项处理模块。
"""

import json
import urllib.parse

from app.logger import setup_logger
from app.service.youzan.event_item import handle_item_event
from app.service.youzan.event_trade import handle_trade_event

logger = setup_logger()


class YouzanEventHandler:
    """有赞系统事件处理器（商品 + 交易 Webhook 双轨合流分发器）。"""

    def __init__(self, db, knowledge_retriever) -> None:
        self._db = db
        self._knowledge = knowledge_retriever

    async def handle_system_event(self, payload: dict, updated_at_str: str, msg_id: str) -> None:
        """
        解析并分发有赞系统事件至对应处理模块。

        参数：
            payload: 有赞 Webhook 原始 payload
            updated_at_str: 事件时间字符串（格式 %Y-%m-%d %H:%M:%S）
            msg_id: 消息去重 ID
        """
        event_type = payload.get("type", "")

        msg_str = urllib.parse.unquote(payload.get("msg", "{}"))
        try:
            msg_obj = json.loads(msg_str)
        except Exception as exc:
            logger.error("解析有赞系统事件 msg 详情失败: %s", exc)
            return

        if event_type.startswith("trade_"):
            await handle_trade_event(
                db=self._db,
                event_type=event_type,
                msg_obj=msg_obj,
                updated_at_str=updated_at_str,
            )
        elif event_type.startswith("item_") or event_type == "ITEM_STATE":
            await handle_item_event(
                db=self._db,
                knowledge_retriever=self._knowledge,
                event_type=event_type,
                msg_obj=msg_obj,
                updated_at_str=updated_at_str,
            )
