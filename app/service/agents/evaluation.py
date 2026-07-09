"""Agent Eval 通用报告模型。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentEvalAssertion:
    """单条 eval 断言结果。"""

    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class AgentEvalCase:
    """单个 Agent eval case。"""

    case_id: str
    agent: str
    query: str
    group: str = ""
    intent: str = ""
    tools: tuple[str, ...] = ()
    assertions: tuple[AgentEvalAssertion, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(assertion.passed for assertion in self.assertions)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.case_id,
            "agent": self.agent,
            "group": self.group,
            "query": self.query,
            "intent": self.intent,
            "tools": list(self.tools),
            "passed": self.passed,
            "assertions": [assertion.to_dict() for assertion in self.assertions],
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class AgentEvalResult:
    """单个 Agent eval 汇总。"""

    agent: str
    cases: tuple[AgentEvalCase, ...]
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def failed(self) -> int:
        return sum(1 for case in self.cases if not case.passed)

    @property
    def status(self) -> str:
        return "passed" if self.failed == 0 else "failed"

    @property
    def pass_rate(self) -> float:
        if not self.total:
            return 0.0
        return round((self.total - self.failed) / self.total, 4)

    def to_dict(self) -> dict[str, object]:
        return {
            "agent": self.agent,
            "status": self.status,
            "total": self.total,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "metadata": self.metadata,
            "cases": [case.to_dict() for case in self.cases],
            "failed_ids": [case.case_id for case in self.cases if not case.passed],
        }


def combine_agent_eval_results(
    results: tuple[AgentEvalResult, ...],
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    """聚合多个 Agent eval 结果。"""
    total = sum(result.total for result in results)
    failed = sum(result.failed for result in results)
    return {
        "status": "passed" if failed == 0 else "failed",
        "total": total,
        "failed": failed,
        "pass_rate": round((total - failed) / total, 4) if total else 0.0,
        "metadata": metadata or {},
        "agents": [result.to_dict() for result in results],
    }
