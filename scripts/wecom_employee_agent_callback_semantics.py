"""企微员工助手回调语义验收规则。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CallbackSemanticRule:
    """单个回调探针的语义约束。"""

    required_any_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()


def is_semantic_safe(content: str, rule: CallbackSemanticRule) -> bool:
    """判断回复是否满足探针语义约束。"""
    if rule.required_any_terms and not any(
        term in content for term in rule.required_any_terms
    ):
        return False
    return not any(term in content for term in rule.forbidden_terms)
