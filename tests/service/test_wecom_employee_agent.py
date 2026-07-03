from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

from app.models.employee_agent import (
    AgentIntent,
    AnswerStyle,
    OrderQueryKind,
    ToolResult,
)
from app.service.wecom import employee_agent_planner
from app.service.wecom.employee_agent_planner import EmployeeAgentPlanner
from app.service.wecom.employee_agent_reply_guard import preserve_tool_facts
from app.service.wecom.employee_agent_service import EmployeeAgentService


class _FakeOrderLookupService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def answer_agent_query(self, query: str, plan: Any) -> ToolResult:
        self.calls.append((query, plan))
        return ToolResult(
            ok=True,
            summary="今天共 2 单，待发货 1 单。",
            next_action="需要处理待发货订单。",
        )


class _FakeActionItemsOrderLookupService:
    async def answer_agent_query(self, query: str, plan: Any) -> ToolResult:
        return ToolResult(
            ok=True,
            summary=(
                "今天有什么要盯的：\n"
                "今天 1 单，合计 206.50 元；发货压力：偏高。\n"
                "待处理 1 单，履约风险 1 单，退款/售后 0 单，无物流 1 单。\n"
                "优先级 1：先处理快到约送时间的履约风险单\n"
                "1. 尾号 000001｜待发货｜巧克力樱桃炸弹 x 1｜206.50 元"
            ),
            next_action="先处理履约风险单，再按无物流、退款/售后顺序核对。",
        )


class _FakeMissingLogisticsOrderLookupService:
    async def answer_agent_query(self, query: str, plan: Any) -> ToolResult:
        return ToolResult(
            ok=True,
            summary=(
                "还没物流的订单有哪些：找到 1 单，按最新订单展示：\n"
                "1. 尾号 000001｜待发货｜巧克力樱桃炸弹 x 1｜206.50 元｜"
                "2026-07-04 10:00｜约送 2026-07-04 16:00｜暂无物流"
            ),
            next_action="列表默认只展示订单尾号，排查时可用尾号继续追问。",
        )


class _FakeBusinessToolService:
    def __init__(self) -> None:
        self.product_payloads: list[dict[str, Any]] = []

    async def lookup_orders(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "result": "订单兜底"}

    async def lookup_products(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.product_payloads.append(payload)
        return {"ok": True, "result": "草莓蛋糕｜库存 6"}

    async def answer_knowledge(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "result": f"知识库回复：{payload.get('question')}。"}


class _FakeBusinessToolServiceWithKnowledgeMiss(_FakeBusinessToolService):
    async def lookup_products(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.product_payloads.append(payload)
        return {
            "ok": True,
            "result": "伯牙绝弦｜258.00元｜库存 72｜生日蛋糕",
            "products": [
                {
                    "title": "伯牙绝弦",
                    "priceFen": 25800,
                    "stock": 72,
                    "categoryName": "生日蛋糕",
                }
            ],
            "nextAction": "库存和价格以小程序商品数据为准，低库存商品建议尽快确认。",
        }

    async def answer_knowledge(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "result": "未找到匹配知识。",
            "nextAction": "员工可复制建议回复；如知识缺失，请到后台知识库补充。",
        }


class _FakeOpsToolService:
    async def lookup_customer(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "result": "找到 1 条地址/客户线索。"}

    async def summarize_group_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "result": f"群活动 {payload.get('campaignId')} 已汇总。",
        }

    async def list_pending_handoffs(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "result": "当前待人工 1 个。"}


class _FakeStatusToolService:
    async def summarize_ops(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "result": "系统状态 attention。"}

    async def summarize_integrations(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "result": "同步失败 0 条。"}

    async def summarize_offline_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "result": "昨晚离线复盘已完成。"}


def _planner() -> EmployeeAgentPlanner:
    return EmployeeAgentPlanner(
        today_provider=lambda: date(2026, 7, 3),
        enable_llm=False,
    )


async def test_planner_builds_today_order_summary_plan() -> None:
    plan = await _planner().plan("今天一共多少订单")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.SUMMARY
    assert plan.query_plan.date_from == "2026-07-03"
    assert plan.query_plan.date_to == "2026-07-03"


async def test_planner_builds_revenue_summary_plan() -> None:
    plan = await _planner().plan("今天营业额多少")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.SUMMARY
    assert plan.query_plan.date_from == "2026-07-03"
    assert plan.query_plan.date_to == "2026-07-03"
    assert plan.query_plan.keyword == ""


async def test_planner_builds_this_week_revenue_summary_plan() -> None:
    plan = await _planner().plan("本周销售额怎么样")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.SUMMARY
    assert plan.query_plan.date_from == "2026-06-29"
    assert plan.query_plan.date_to == "2026-07-03"
    assert plan.query_plan.keyword == ""


async def test_planner_builds_this_month_revenue_summary_plan() -> None:
    plan = await _planner().plan("本月销售额怎么样")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.SUMMARY
    assert plan.query_plan.date_from == "2026-07-01"
    assert plan.query_plan.date_to == "2026-07-03"
    assert plan.query_plan.keyword == ""


async def test_planner_builds_refund_order_summary_plan() -> None:
    plan = await _planner().plan("今天有退款订单吗")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.SUMMARY
    assert plan.query_plan.date_from == "2026-07-03"
    assert plan.query_plan.date_to == "2026-07-03"
    assert plan.query_plan.needs_refund is True
    assert plan.query_plan.keyword == ""


async def test_planner_builds_last_week_refund_summary_plan() -> None:
    plan = await _planner().plan("上周退款多少")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.SUMMARY
    assert plan.query_plan.date_from == "2026-06-22"
    assert plan.query_plan.date_to == "2026-06-28"
    assert plan.query_plan.needs_refund is True
    assert plan.query_plan.keyword == ""


async def test_planner_builds_fulfillment_risk_list_plan() -> None:
    plan = await _planner().plan("哪些单快超时了")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.LIST
    assert plan.query_plan.statuses == (
        "WAIT_SELLER_SEND_GOODS",
        "WAIT_BUYER_CONFIRM_GOODS",
    )
    assert plan.query_plan.needs_fulfillment_risk is True
    assert plan.query_plan.sort_by == "delivery_time"
    assert plan.query_plan.keyword == ""


async def test_planner_builds_order_action_items_plan() -> None:
    plan = await _planner().plan("今天有什么要盯的")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.ACTION_ITEMS
    assert plan.answer_style == AnswerStyle.ACTION_ITEMS
    assert plan.query_plan.date_from == "2026-07-03"
    assert plan.query_plan.date_to == "2026-07-03"
    assert plan.query_plan.keyword == ""


async def test_planner_keeps_refund_policy_as_knowledge() -> None:
    plan = await _planner().plan("退款规则是什么")

    assert plan.intent == AgentIntent.KNOWLEDGE_ANSWER
    assert plan.tools == ("knowledge_answer",)
    assert plan.query_plan is None


async def test_planner_builds_order_knowledge_multi_tool_plan() -> None:
    plan = await _planner().plan("还有哪些没发货，怎么跟客户说")

    assert plan.intent == AgentIntent.MULTI_TOOL
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.LIST
    assert plan.query_plan.statuses == ("WAIT_SELLER_SEND_GOODS",)
    assert plan.tools == ("order_dynamic_query", "knowledge_answer")


async def test_planner_builds_pending_order_list_plan() -> None:
    plan = await _planner().plan("还有哪些没发货")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.statuses == ("WAIT_SELLER_SEND_GOODS",)


async def test_planner_builds_evening_pending_order_window_plan() -> None:
    plan = await _planner().plan("晚上还有哪些待处理订单")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.LIST
    assert plan.query_plan.date_from == "2026-07-03"
    assert plan.query_plan.date_to == "2026-07-03"
    assert plan.query_plan.date_field == "delivery_time"
    assert plan.query_plan.statuses == (
        "WAIT_SELLER_SEND_GOODS",
        "WAIT_BUYER_CONFIRM_GOODS",
    )
    assert plan.query_plan.delivery_time_start == "18:00"
    assert plan.query_plan.delivery_time_end == "23:59"
    assert plan.query_plan.keyword == ""


async def test_planner_builds_tomorrow_pending_delivery_date_plan() -> None:
    plan = await _planner().plan("明天有哪些待处理订单")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.LIST
    assert plan.query_plan.date_from == "2026-07-04"
    assert plan.query_plan.date_to == "2026-07-04"
    assert plan.query_plan.date_field == "delivery_time"
    assert plan.query_plan.statuses == (
        "WAIT_SELLER_SEND_GOODS",
        "WAIT_BUYER_CONFIRM_GOODS",
    )
    assert plan.query_plan.keyword == ""


async def test_planner_builds_after_tomorrow_pending_delivery_date_plan() -> None:
    plan = await _planner().plan("后天有哪些待处理订单")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.LIST
    assert plan.query_plan.date_from == "2026-07-05"
    assert plan.query_plan.date_to == "2026-07-05"
    assert plan.query_plan.date_field == "delivery_time"
    assert plan.query_plan.statuses == (
        "WAIT_SELLER_SEND_GOODS",
        "WAIT_BUYER_CONFIRM_GOODS",
    )
    assert plan.query_plan.keyword == ""


async def test_planner_builds_weekend_pending_delivery_date_plan() -> None:
    plan = await _planner().plan("周末有哪些待处理订单")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.LIST
    assert plan.query_plan.date_from == "2026-07-04"
    assert plan.query_plan.date_to == "2026-07-05"
    assert plan.query_plan.date_field == "delivery_time"
    assert plan.query_plan.statuses == (
        "WAIT_SELLER_SEND_GOODS",
        "WAIT_BUYER_CONFIRM_GOODS",
    )
    assert plan.query_plan.keyword == ""


async def test_planner_builds_next_monday_pending_delivery_date_plan() -> None:
    plan = await _planner().plan("下周一有哪些待处理订单")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.LIST
    assert plan.query_plan.date_from == "2026-07-06"
    assert plan.query_plan.date_to == "2026-07-06"
    assert plan.query_plan.date_field == "delivery_time"
    assert plan.query_plan.statuses == (
        "WAIT_SELLER_SEND_GOODS",
        "WAIT_BUYER_CONFIRM_GOODS",
    )
    assert plan.query_plan.keyword == ""


async def test_planner_builds_product_order_multi_tool_plan() -> None:
    plan = await _planner().plan("椰椰凤梨今天卖了几单，库存还够吗")

    assert plan.intent == AgentIntent.MULTI_TOOL
    assert plan.query_plan is not None
    assert plan.query_plan.keyword == "椰椰凤梨"
    assert plan.tools == ("order_dynamic_query", "product_lookup")


async def test_planner_builds_top_products_plan() -> None:
    plan = await _planner().plan("今天哪个商品卖得多")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.TOP_PRODUCTS
    assert plan.query_plan.date_from == "2026-07-03"


async def test_planner_builds_recent_days_order_range_plan() -> None:
    plan = await _planner().plan("最近3天椰椰凤梨卖了几单")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.SUMMARY
    assert plan.query_plan.date_from == "2026-07-01"
    assert plan.query_plan.date_to == "2026-07-03"
    assert plan.query_plan.keyword == "椰椰凤梨"


async def test_planner_builds_month_day_order_range_plan() -> None:
    plan = await _planner().plan("7月5日椰椰凤梨卖了几单")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.SUMMARY
    assert plan.query_plan.date_from == "2026-07-05"
    assert plan.query_plan.date_to == "2026-07-05"
    assert plan.query_plan.keyword == "椰椰凤梨"


async def test_planner_builds_weekday_order_range_plan() -> None:
    plan = await _planner().plan("周五椰椰凤梨卖了几单")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.SUMMARY
    assert plan.query_plan.date_from == "2026-07-03"
    assert plan.query_plan.date_to == "2026-07-03"
    assert plan.query_plan.keyword == "椰椰凤梨"


async def test_planner_builds_this_week_order_range_plan() -> None:
    plan = await _planner().plan("本周哪个商品卖得多")

    assert plan.intent == AgentIntent.ORDER_QUERY
    assert plan.query_plan is not None
    assert plan.query_plan.kind == OrderQueryKind.TOP_PRODUCTS
    assert plan.query_plan.date_from == "2026-06-29"
    assert plan.query_plan.date_to == "2026-07-03"
    assert plan.query_plan.keyword == ""


async def test_planner_routes_knowledge_and_ops() -> None:
    knowledge_plan = await _planner().plan("配送范围怎么说")
    casual_delivery_plan = await _planner().plan("明天能配送吗")
    ops_plan = await _planner().plan("系统今天有没有异常")
    customer_plan = await _planner().plan("查一下张三地址线索")
    campaign_plan = await _planner().plan("汇总 campaignId:abc123")
    offline_review_plan = await _planner().plan("昨晚离线复盘结果")

    assert knowledge_plan.intent == AgentIntent.KNOWLEDGE_ANSWER
    assert casual_delivery_plan.intent == AgentIntent.KNOWLEDGE_ANSWER
    assert ops_plan.intent == AgentIntent.OPS_QUERY
    assert customer_plan.tools == ("customer_lookup",)
    assert campaign_plan.tools == ("group_campaign_summary",)
    assert offline_review_plan.tools == ("offline_review_summary",)


async def test_planner_routes_casual_inventory_question_to_product() -> None:
    plan = await _planner().plan("伯牙绝弦还有吗")

    assert plan.intent == AgentIntent.PRODUCT_QUERY
    assert plan.tools == ("product_lookup",)


async def test_planner_builds_product_knowledge_multi_tool_plan() -> None:
    replacement_plan = await _planner().plan("伯牙绝弦库存不够怎么推荐替代")
    reply_plan = await _planner().plan("伯牙绝弦没货怎么跟客户说")

    assert replacement_plan.intent == AgentIntent.MULTI_TOOL
    assert replacement_plan.tools == ("product_lookup", "knowledge_answer")
    assert replacement_plan.query_plan is None
    assert reply_plan.intent == AgentIntent.MULTI_TOOL
    assert reply_plan.tools == ("product_lookup", "knowledge_answer")
    assert reply_plan.query_plan is None


async def test_planner_gives_llm_all_capabilities_when_search_is_empty(
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}

    async def fake_llm_chat(
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> SimpleNamespace:
        captured["prompt"] = messages[0]["content"]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            '{"intent":"product_query","tools":["product_lookup"],'
                            '"queryPlan":null,"answerStyle":"summary"}'
                        )
                    )
                )
            ]
        )

    monkeypatch.setattr(employee_agent_planner, "llm_chat", fake_llm_chat)

    plan = await EmployeeAgentPlanner(
        today_provider=lambda: date(2026, 7, 3),
        enable_llm=True,
    ).plan("伯牙绝弦")

    assert plan.intent == AgentIntent.PRODUCT_QUERY
    assert "product_lookup" in captured["prompt"]
    assert "order_dynamic_query" in captured["prompt"]


async def test_employee_agent_uses_order_lookup_service() -> None:
    order_lookup_service = _FakeOrderLookupService()
    service = EmployeeAgentService(
        business_tool_service=_FakeBusinessToolService(),
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        order_lookup_service=order_lookup_service,
        planner=_planner(),
        enable_llm_reply=False,
    )

    reply = await service.answer("今天一共多少订单")

    assert "今天共 2 单" in reply
    assert "下一步：需要处理待发货订单。" in reply
    assert order_lookup_service.calls[0][1].kind == OrderQueryKind.SUMMARY


async def test_employee_agent_order_reply_does_not_ask_for_full_order_no() -> None:
    service = EmployeeAgentService(
        business_tool_service=_FakeBusinessToolService(),
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        order_lookup_service=_FakeOrderLookupService(),
        planner=_planner(),
        enable_llm_reply=False,
    )

    reply = await service.answer("今天一共多少订单")

    assert "完整订单号" not in reply
    assert "订单尾号" not in reply or "完整" not in reply


async def test_employee_agent_routes_product_and_knowledge() -> None:
    business_tool_service = _FakeBusinessToolService()
    service = EmployeeAgentService(
        business_tool_service=business_tool_service,
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        planner=_planner(),
        enable_llm_reply=False,
    )

    product_reply = await service.answer("草莓蛋糕还有库存吗")
    knowledge_reply = await service.answer("配送范围怎么说")

    assert "库存 6" in product_reply
    assert "配送范围" in knowledge_reply
    assert business_tool_service.product_payloads[0]["query"] == "草莓蛋糕还有库存吗"


async def test_employee_agent_multi_tool_uses_order_keyword_for_product() -> None:
    business_tool_service = _FakeBusinessToolService()
    service = EmployeeAgentService(
        business_tool_service=business_tool_service,
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        order_lookup_service=_FakeOrderLookupService(),
        planner=_planner(),
        enable_llm_reply=False,
    )

    await service.answer("今天订单里有伯牙绝弦吗，库存还够吗")

    assert business_tool_service.product_payloads[0]["query"] == "伯牙绝弦"


async def test_employee_agent_multi_tool_combines_order_and_knowledge() -> None:
    service = EmployeeAgentService(
        business_tool_service=_FakeBusinessToolService(),
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        order_lookup_service=_FakeOrderLookupService(),
        planner=_planner(),
        enable_llm_reply=False,
    )

    reply = await service.answer("还有哪些没发货，怎么跟客户说")

    assert "今天共 2 单" in reply
    assert "知识库回复：还有哪些没发货，怎么跟客户说。" in reply


async def test_employee_agent_multi_tool_combines_product_and_knowledge() -> None:
    business_tool_service = _FakeBusinessToolService()
    service = EmployeeAgentService(
        business_tool_service=business_tool_service,
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        planner=_planner(),
        enable_llm_reply=False,
    )

    reply = await service.answer("伯牙绝弦库存不够怎么推荐替代")

    assert "库存 6" in reply
    assert "知识库回复：伯牙绝弦库存不够怎么推荐替代。" in reply
    assert business_tool_service.product_payloads[0]["query"] == (
        "伯牙绝弦库存不够怎么推荐替代"
    )


async def test_employee_agent_product_knowledge_miss_uses_staff_reply() -> None:
    business_tool_service = _FakeBusinessToolServiceWithKnowledgeMiss()
    service = EmployeeAgentService(
        business_tool_service=business_tool_service,
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        planner=_planner(),
        enable_llm_reply=False,
    )

    reply = await service.answer("伯牙绝弦库存不够怎么推荐替代")

    assert "库存 72" in reply
    assert "未找到匹配知识" not in reply
    assert "不要直接说没货" in reply
    assert "推荐" in reply
    assert "替代款" in reply
    assert "客户" in reply


async def test_employee_agent_routes_existing_ops_tools() -> None:
    service = EmployeeAgentService(
        business_tool_service=_FakeBusinessToolService(),
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        planner=_planner(),
        enable_llm_reply=False,
    )

    customer_reply = await service.answer("查一下张三地址线索")
    campaign_reply = await service.answer("汇总 campaignId:abc123")
    offline_review_reply = await service.answer("昨晚离线复盘结果")

    assert "地址/客户线索" in customer_reply
    assert "abc123" in campaign_reply
    assert "离线复盘" in offline_review_reply


async def test_employee_agent_knowledge_reply_skips_llm_polish(monkeypatch) -> None:
    async def fail_llm_chat(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("knowledge reply should not call LLM polish")

    monkeypatch.setattr(
        "app.service.wecom.employee_agent_service.llm_chat", fail_llm_chat
    )
    service = EmployeeAgentService(
        business_tool_service=_FakeBusinessToolService(),
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        planner=_planner(),
        enable_llm_reply=True,
    )

    reply = await service.answer("明天能配送吗")

    assert "知识库回复：明天能配送吗。" in reply


async def test_employee_agent_ops_reply_skips_llm_polish(monkeypatch) -> None:
    async def fail_llm_chat(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("ops reply should not call LLM polish")

    monkeypatch.setattr(
        "app.service.wecom.employee_agent_service.llm_chat", fail_llm_chat
    )
    service = EmployeeAgentService(
        business_tool_service=_FakeBusinessToolService(),
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        planner=_planner(),
        enable_llm_reply=True,
    )

    reply = await service.answer("查一下张三地址线索")

    assert "地址/客户线索" in reply


async def test_employee_agent_polish_keeps_product_stock_number(monkeypatch) -> None:
    async def fake_llm_chat(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="建议回复客户：这款库存紧张，可以推荐替代款。"
                    )
                )
            ]
        )

    monkeypatch.setattr(
        "app.service.wecom.employee_agent_service.llm_chat", fake_llm_chat
    )
    service = EmployeeAgentService(
        business_tool_service=_FakeBusinessToolService(),
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        planner=_planner(),
        enable_llm_reply=True,
    )

    reply = await service.answer("伯牙绝弦库存不够怎么推荐替代")

    assert "库存 6" in reply
    assert "知识库回复" in reply


async def test_employee_agent_polish_drops_private_marker(monkeypatch) -> None:
    async def fake_llm_chat(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="有 2 单未发货，请让员工提供完整订单号再回复客户。"
                    )
                )
            ]
        )

    monkeypatch.setattr(
        "app.service.wecom.employee_agent_service.llm_chat", fake_llm_chat
    )
    service = EmployeeAgentService(
        business_tool_service=_FakeBusinessToolService(),
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        order_lookup_service=_FakeOrderLookupService(),
        planner=_planner(),
        enable_llm_reply=True,
    )

    reply = await service.answer("还有哪些没发货，怎么跟客户说")

    assert "完整订单号" not in reply
    assert "今天共 2 单" in reply


async def test_employee_agent_polish_keeps_action_insight_markers(
    monkeypatch,
) -> None:
    async def fake_llm_chat(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=(
                            "今天需重点处理1单：优先处理尾号000001，"
                            "约送16:00，暂无物流。"
                        )
                    )
                )
            ]
        )

    monkeypatch.setattr(
        "app.service.wecom.employee_agent_service.llm_chat", fake_llm_chat
    )
    service = EmployeeAgentService(
        business_tool_service=_FakeBusinessToolService(),
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        order_lookup_service=_FakeActionItemsOrderLookupService(),
        planner=_planner(),
        enable_llm_reply=True,
    )

    reply = await service.answer("今天有什么要盯的")

    assert "发货压力：偏高" in reply
    assert "优先级 1" in reply


async def test_employee_agent_polish_keeps_missing_logistics_marker(
    monkeypatch,
) -> None:
    async def fake_llm_chat(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="当前有1单未发货，请优先处理尾号000001。"
                    )
                )
            ]
        )

    monkeypatch.setattr(
        "app.service.wecom.employee_agent_service.llm_chat", fake_llm_chat
    )
    service = EmployeeAgentService(
        business_tool_service=_FakeBusinessToolService(),
        ops_tool_service=_FakeOpsToolService(),
        status_tool_service=_FakeStatusToolService(),
        order_lookup_service=_FakeMissingLogisticsOrderLookupService(),
        planner=_planner(),
        enable_llm_reply=True,
    )

    reply = await service.answer("还没物流的订单有哪些")

    assert "暂无物流" in reply


def test_preserve_tool_facts_rejects_private_marker_introduced_by_polish() -> None:
    deterministic_reply = "当前有 2 单未发货，均只展示尾号。"
    polished_reply = "当前有 2 单未发货，请提供完整订单号排查。"

    reply = preserve_tool_facts(polished_reply, deterministic_reply)

    assert reply == deterministic_reply


def test_preserve_tool_facts_rejects_missing_logistics_marker() -> None:
    deterministic_reply = (
        "还没物流的订单有哪些：找到 1 单。\n"
        "1. 尾号 000001｜待发货｜巧克力樱桃炸弹｜暂无物流"
    )
    polished_reply = "当前有1单未发货，请优先处理尾号000001。"

    reply = preserve_tool_facts(polished_reply, deterministic_reply)

    assert reply == deterministic_reply


def test_preserve_tool_facts_rejects_missing_action_insight_marker() -> None:
    deterministic_reply = (
        "今天 1 单，合计 206.50 元；发货压力：偏高。\n"
        "优先级 1：先处理快到约送时间的履约风险单"
    )
    polished_reply = "今天需重点处理1单：优先处理尾号000001。"

    reply = preserve_tool_facts(polished_reply, deterministic_reply)

    assert reply == deterministic_reply


def test_preserve_tool_facts_rejects_missing_pressure_label() -> None:
    deterministic_reply = (
        "今天发货压力大不大：找到 5 单，按最新订单展示：\n"
        "发货压力：偏高。待处理 5 单，履约风险 5 单。"
    )
    polished_reply = "今天发货压力不大，目前仅5单待处理。"

    reply = preserve_tool_facts(polished_reply, deterministic_reply)

    assert reply == deterministic_reply


def test_preserve_tool_facts_rejects_empty_order_detour() -> None:
    deterministic_reply = (
        "晚上还有哪些待处理订单：没有查到约送日期 2026-07-04、"
        "约送时间 18:00-23:59、待处理的订单。\n"
        "下一步：这表示当前约送口径下暂无待处理订单；可继续问其他日期或查看今日待办。"
    )
    polished_reply = "没有查到待处理订单。建议换商品名、状态或时间范围再查。"

    reply = preserve_tool_facts(polished_reply, deterministic_reply)

    assert reply == deterministic_reply
