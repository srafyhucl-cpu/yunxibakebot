"""企微员工助手回调语义验收规则。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CallbackSemanticRule:
    """单个回调探针的语义约束。"""

    required_any_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()


CALLBACK_SEMANTIC_RULES: dict[str, CallbackSemanticRule] = {
    "today-order-summary": CallbackSemanticRule(
        required_any_terms=("单",),
        forbidden_terms=("完整订单号",),
    ),
    "pending-shipment-list": CallbackSemanticRule(
        required_any_terms=("待发货", "未发货"),
        forbidden_terms=("完整订单号", "手机号"),
    ),
    "missing-logistics-list": CallbackSemanticRule(
        required_any_terms=("物流",),
        forbidden_terms=("完整订单号", "手机号"),
    ),
    "product-order-summary": CallbackSemanticRule(
        required_any_terms=("单",),
        forbidden_terms=("完整订单号", "手机号"),
    ),
    "top-products": CallbackSemanticRule(
        required_any_terms=("销量",),
        forbidden_terms=("完整订单号", "手机号"),
    ),
    "order-product-inventory": CallbackSemanticRule(
        required_any_terms=("库存",),
        forbidden_terms=("完整订单号", "手机号"),
    ),
    "casual-inventory": CallbackSemanticRule(
        required_any_terms=("库存",),
        forbidden_terms=("完整订单号", "手机号"),
    ),
    "delivery-knowledge": CallbackSemanticRule(
        required_any_terms=("配送",),
        forbidden_terms=("订单尾号", "订单状态", "订单页", "后台订单"),
    ),
    "ops-status": CallbackSemanticRule(
        required_any_terms=("系统",),
        forbidden_terms=("完整订单号", "手机号"),
    ),
    "handoff-pending": CallbackSemanticRule(
        required_any_terms=("待人工", "转人工"),
        forbidden_terms=("买家", "ID:", "user"),
    ),
}


def semantic_rule_for(probe_name: str) -> CallbackSemanticRule:
    """返回探针对应的语义规则。"""
    return CALLBACK_SEMANTIC_RULES.get(probe_name, CallbackSemanticRule())


def is_semantic_safe(content: str, rule: CallbackSemanticRule) -> bool:
    """判断回复是否满足探针语义约束。"""
    if rule.required_any_terms and not any(
        term in content for term in rule.required_any_terms
    ):
        return False
    return not any(term in content for term in rule.forbidden_terms)
