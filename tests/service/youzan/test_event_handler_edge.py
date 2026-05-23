"""
event_handler / event_item 边界场景测试：
1. youzan API 返回非 dict 响应（str）时不应抛 AttributeError
2. alias 为空时写库不应触发 NOT NULL / UNIQUE 约束
"""
import json
import pytest
import aiosqlite

from app.database import init_db
from app.repository.session_repo import SessionRepo
from app.repository.message_repo import MessageRepo
from app.repository.transfer_repo import TransferRepo
from app.service.youzan.event_handler import YouzanEventHandler
from app.service.youzan.client import YouzanClient
from app.service.knowledge_retriever import KnowledgeRetriever
from app.service.embedding_search import EmbeddingSearcher
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.config_repo import ConfigRepo


class _FakeYouzanClient:
    """模拟有赞 API 返回字符串（非 dict）的极端场景。"""
    async def get_product(self, item_id, alias=""):
        return "商品不存在"  # 模拟 HTTP 200 + JSON string body

    async def get_order(self, *a, **kw):
        return {}


class _FakeYouzanClientStringData:
    """模拟 msg_obj[data] 为字符串的有赞老格式事件极端场景。"""
    async def get_product(self, item_id, alias=""):
        return {
            "response": {
                "item": {
                    "title": "测试商品",
                    "alias": "",
                    "price": 9800,
                    "quantity": 5,
                    "pic_url": "",
                    "desc": "",
                    "skus": [],
                    "item_props": [],
                }
            }
        }

    async def get_order(self, *a, **kw):
        return {}


class _FakeYouzanClientEmptyAlias:
    """模拟有赞 API 返回 alias 为空的正常 dict 响应。"""
    async def get_product(self, item_id, alias=""):
        return {
            "response": {
                "item": {
                    "title": "测试商品",
                    "alias": "",
                    "price": 9800,
                    "quantity": 10,
                    "pic_url": "",
                    "desc": "",
                    "skus": [],
                    "item_props": [],
                }
            }
        }

    async def get_order(self, *a, **kw):
        return {}


@pytest.mark.asyncio
async def test_api_returns_string_no_crash():
    """有赞 API 返回 str 时 event_item 不应抛 AttributeError（响应结构异常，正常记录 ERROR 并跳过）。"""
    db = await init_db(":memory:")
    vs = EmbeddingSearcher()
    vs.build([])
    kr = KnowledgeRetriever(KnowledgeRepo(db), vs, config_repo=ConfigRepo(db))
    handler = YouzanEventHandler(db=db, knowledge_retriever=kr, youzan_client=_FakeYouzanClient())

    payload = {
        "type": "ITEM_STATE",
        "msg": json.dumps({"item_id": 1234}),
        "id": "test_msg_001",
    }
    await handler.handle_system_event(
        payload=payload,
        event_type="ITEM_STATE",
        updated_at_str="2026-05-23 13:00:00",
        msg_id="test_msg_001",
    )
    await db.close()


@pytest.mark.asyncio
async def test_msg_obj_data_string_no_crash():
    """msg_obj[data] 为字符串时，item_ 分支不应在 try/except 外崩溃。"""
    db = await init_db(":memory:")
    vs = EmbeddingSearcher()
    vs.build([])
    kr = KnowledgeRetriever(KnowledgeRepo(db), vs, config_repo=ConfigRepo(db))
    handler = YouzanEventHandler(db=db, knowledge_retriever=kr, youzan_client=_FakeYouzanClientStringData())

    # msg 中 data 字段为字符串（有赞老格式）
    payload = {
        "type": "ITEM_STATE",
        "msg": json.dumps({"data": "100010", "item_id": 100010}),
        "id": "test_msg_002",
    }
    await handler.handle_system_event(
        payload=payload,
        event_type="ITEM_STATE",
        updated_at_str="2026-05-23 13:00:00",
        msg_id="test_msg_002",
    )
    # 验证商品已写入 DB（alias 兜底为 str(item_id)）
    rows = await db.execute_fetchall(
        "SELECT item_id, alias FROM youzan_products WHERE item_id = 100010"
    )
    assert len(rows) == 1
    assert rows[0]["alias"] == "100010"  # 兜底值
    await db.close()


@pytest.mark.asyncio
async def test_empty_alias_uses_item_id_fallback():
    """alias 为空字符串时应用 str(item_id) 兜底，两条不同商品均能写入。"""
    db = await init_db(":memory:")
    vs = EmbeddingSearcher()
    vs.build([])
    kr = KnowledgeRetriever(KnowledgeRepo(db), vs, config_repo=ConfigRepo(db))
    handler = YouzanEventHandler(db=db, knowledge_retriever=kr, youzan_client=_FakeYouzanClientEmptyAlias())

    for item_id, msg_id in [(100010, "msg_a"), (99999, "msg_b")]:
        payload = {
            "type": "ITEM_STATE",
            "msg": json.dumps({"item_id": item_id}),
            "id": msg_id,
        }
        await handler.handle_system_event(
            payload=payload,
            event_type="ITEM_STATE",
            updated_at_str="2026-05-23 13:00:00",
            msg_id=msg_id,
        )
    # 两条均应写入，alias 分别兜底为各自 item_id
    rows = await db.execute_fetchall(
        "SELECT item_id, alias FROM youzan_products ORDER BY item_id"
    )
    assert len(rows) == 2
    assert {r["alias"] for r in rows} == {"99999", "100010"}
    await db.close()
