"""企微员工助手回调语义验收规则。"""

from __future__ import annotations

from dataclasses import dataclass
import re

PLAIN_TEXT_FORBIDDEN_MARKERS = ("**", "__", "`")
BLOCKQUOTE_MARK_PATTERN = re.compile(r"(?m)^>\s*")


@dataclass(frozen=True)
class CallbackSemanticRule:
    """单个回调探针的语义约束。"""

    required_any_terms: tuple[str, ...] = ()
    required_all_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()


def is_semantic_safe(content: str, rule: CallbackSemanticRule) -> bool:
    """判断回复是否满足探针语义约束。"""
    if rule.required_any_terms and not any(
        term in content for term in rule.required_any_terms
    ):
        return False
    if rule.required_all_terms and not all(
        term in content for term in rule.required_all_terms
    ):
        return False
    return not any(term in content for term in rule.forbidden_terms)


def has_plain_text_violation(content: str) -> bool:
    """企微员工助手 stream 回复必须是纯文本，不保留 Markdown 装饰。"""
    return any(marker in content for marker in PLAIN_TEXT_FORBIDDEN_MARKERS) or bool(
        BLOCKQUOTE_MARK_PATTERN.search(content)
    )
