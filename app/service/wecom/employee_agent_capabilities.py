"""企微员工助手能力检索。"""

from __future__ import annotations

from dataclasses import dataclass


CAPABILITY_MATCH_LIMIT = 3


@dataclass(frozen=True)
class AgentCapabilityCard:
    """员工助手可调用能力说明卡。"""

    name: str
    intent: str
    description: str
    examples: tuple[str, ...]
    keywords: tuple[str, ...]


CAPABILITY_CARDS: tuple[AgentCapabilityCard, ...] = (
    AgentCapabilityCard(
        name="order_dynamic_query",
        intent="order_query",
        description="查询有赞订单、今日订单、最近订单、待发货、待收货、未发货、物流缺失、商品销量和订单统计。",
        examples=(
            "今天一共多少订单",
            "还有哪些没发货",
            "椰椰凤梨今天卖了几单",
            "最近订单",
        ),
        keywords=("订单", "下单", "发货", "物流", "卖了", "几单", "多少单", "待处理"),
    ),
    AgentCapabilityCard(
        name="product_lookup",
        intent="product_query",
        description="查询商品价格、库存、分类、上架状态和商品推荐。",
        examples=("草莓蛋糕还有库存吗", "伯牙绝弦多少钱", "今天还有什么蛋糕"),
        keywords=(
            "商品",
            "库存",
            "价格",
            "蛋糕",
            "面包",
            "甜品",
            "多少钱",
            "还有吗",
            "还够",
            "够吗",
            "上架",
        ),
    ),
    AgentCapabilityCard(
        name="knowledge_answer",
        intent="knowledge_answer",
        description="查询门店规则、配送范围、售后话术、常见问题和员工可复制回复。",
        examples=("配送范围怎么说", "退款规则是什么", "自提怎么回复客户"),
        keywords=("规则", "怎么说", "话术", "配送范围", "配送", "退款", "自提", "售后"),
    ),
    AgentCapabilityCard(
        name="ops_summary",
        intent="ops_query",
        description="查询系统状态、观察台、同步失败、Webhook 异常和离线复盘。",
        examples=("系统今天有没有异常", "同步失败有哪些", "昨晚复盘怎么样"),
        keywords=("系统", "异常", "观察台", "同步失败", "webhook", "复盘"),
    ),
    AgentCapabilityCard(
        name="handoff_pending",
        intent="ops_query",
        description="查询待人工、转人工、待接单工单和需要员工处理的会话。",
        examples=("现在有哪些待人工", "待接单还有几个"),
        keywords=("待人工", "转人工", "待接单", "人工处理"),
    ),
)


class EmployeeAgentCapabilityRegistry:
    """基于能力卡的轻量 RAG 检索。"""

    def all_cards(self) -> list[AgentCapabilityCard]:
        """返回全量能力卡，供 LLM 在弱关键词问法下兜底规划。"""
        return list(CAPABILITY_CARDS)

    def search(
        self, query: str, limit: int = CAPABILITY_MATCH_LIMIT
    ) -> list[AgentCapabilityCard]:
        normalized_query = query.lower()
        scored_cards = [
            (_score_card(normalized_query, card), card) for card in CAPABILITY_CARDS
        ]
        matched_cards = [
            card
            for score, card in sorted(
                scored_cards,
                key=lambda item: (-item[0], item[1].name),
            )
            if score > 0
        ]
        return matched_cards[:limit]


def _score_card(normalized_query: str, card: AgentCapabilityCard) -> int:
    keyword_score = sum(
        1 for keyword in card.keywords if keyword.lower() in normalized_query
    )
    example_score = sum(
        1 for example in card.examples if example.lower() in normalized_query
    )
    return keyword_score + example_score
