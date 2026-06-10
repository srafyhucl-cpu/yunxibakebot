"""Build concise handoff notes for human servicers."""

from __future__ import annotations

import re

MAX_NOTE_LENGTH = 180
MAX_ISSUES = 2
ELDER_HINTS = ("老人", "长辈", "老年", "爷爷", "奶奶", "外公", "外婆", "爸爸", "妈妈")
LOW_SUGAR_HINTS = ("木糖醇", "低糖", "少糖", "无糖", "控糖")
SIZE_HINT_RE = re.compile(r"\d+\s*(?:个|人|寸)")
NEGATIVE_HINTS = ("不适合", "不满意", "不对", "不喜欢", "算了", "投诉")


def build_handoff_note(reason: str, history_text: str) -> str:
    """Turn recent dialog into a short decision note for a servicer."""
    lines = _dialog_lines(history_text)
    user_text = "；".join(content for role, content in lines if role == "用户")
    ai_text = "；".join(content for role, content in lines if role == "AI")

    needs = _collect_needs(user_text)
    issues = _collect_issues(user_text, ai_text)
    suggestion = _build_suggestion(user_text, ai_text)

    parts: list[str] = []
    if needs:
        parts.append(f"客户诉求：{'，'.join(needs)}")
    if issues:
        parts.append(f"当前卡点：{'，'.join(issues[:MAX_ISSUES])}")
    if suggestion:
        parts.append(f"建议接手：{suggestion}")
    if not parts:
        compact_reason = _compact(reason)
        parts.append(
            f"客户请求人工接待{f'：{compact_reason}' if compact_reason else ''}"
        )

    return _limit_note("；".join(parts))


def _dialog_lines(history_text: str) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    for raw_line in history_text.splitlines():
        line = _compact(raw_line).lstrip("- ")
        if not line:
            continue
        if line.startswith("用户："):
            lines.append(("用户", line.removeprefix("用户：")))
        elif line.startswith("AI："):
            lines.append(("AI", line.removeprefix("AI：")))
    return lines


def _collect_needs(user_text: str) -> list[str]:
    needs: list[str] = []
    if any(hint in user_text for hint in ELDER_HINTS):
        needs.append("给老人/长辈选蛋糕")
    if any(hint in user_text for hint in LOW_SUGAR_HINTS):
        needs.append("偏木糖醇/低糖")
    size_hints = SIZE_HINT_RE.findall(user_text)
    if size_hints:
        needs.append(f"人数/尺寸：{size_hints[-1].replace(' ', '')}")
    return needs


def _collect_issues(user_text: str, ai_text: str) -> list[str]:
    issues: list[str] = []
    if any(hint in user_text for hint in NEGATIVE_HINTS):
        issues.append("客户已表达推荐不认可")
    if "星星人" in user_text or "星星人" in ai_text:
        issues.append("星星人款式被提及，长辈场景需避开潮玩感")
    return issues


def _build_suggestion(user_text: str, ai_text: str) -> str:
    combined = user_text + "；" + ai_text
    if any(hint in combined for hint in ELDER_HINTS):
        return "先致歉，优先推荐祝寿/稳重/寓意明确款，确认甜度和尺寸。"
    if any(hint in user_text for hint in NEGATIVE_HINTS):
        return "先承接不满，再缩小需求后推荐。"
    return ""


def _compact(text: str) -> str:
    return " ".join(str(text or "").split())


def _limit_note(note: str) -> str:
    if len(note) <= MAX_NOTE_LENGTH:
        return note
    return note[: MAX_NOTE_LENGTH - 1] + "…"
