"""真人紧急呼叫通知中心单元测试。"""

import pytest

from app.config import settings
from app.models.transfer import HumanTransfer, TransferStatus
from app.repository.transfer_repo import TransferRepo
from app.service.transfer_manager import TransferManager


class MockTransferRepo(TransferRepo):
    """虚拟的数据层，不与 real db 发生交互。"""

    def __init__(self) -> None:
        pass

    async def create(
        self, session_id: str, user_id: str, reason: str = "", summary: str = ""
    ) -> HumanTransfer:
        return HumanTransfer(
            id="test_transfer_001",
            session_id=session_id,
            user_id=user_id,
            reason=reason,
            conversation_summary=summary,
            status=TransferStatus.PENDING,
            created_at="0.0",
            accepted_at="",
            closed_at="",
        )


class CapturingTransferManager(TransferManager):
    def __init__(self, repo: TransferRepo) -> None:
        super().__init__(repo)
        self.notified_messages: list[str] = []

    async def notify_staff_emergency(self, session_id: str, last_message: str) -> None:
        self.notified_messages.append(last_message)


@pytest.mark.asyncio
async def test_transfer_manager_notifies_with_summary_first() -> None:
    repo = MockTransferRepo()
    mgr = CapturingTransferManager(repo)

    transfer = await mgr.request_transfer(
        session_id="session-summary",
        user_id="buyer-summary",
        reason="转人工",
        summary="转人工触发：用户要求转人工\n最近对话：\n- 用户想订草莓千层，少糖",
    )

    assert transfer.conversation_summary.startswith("转人工触发")
    assert mgr.notified_messages == [transfer.conversation_summary]


@pytest.mark.asyncio
async def test_transfer_manager_emergency_notification_triggers_correctly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试当触发 request_transfer 判定为转人工时，紧急呼叫通知中心被完美触发。"""
    # 1. 模拟企微配置
    monkeypatch.setattr(
        settings,
        "WECOM_ROBOT_WEBHOOK",
        "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=mock_key",
    )
    monkeypatch.setattr(settings, "WECOM_CORP_ID", "mock_corp_id")
    monkeypatch.setattr(settings, "WECOM_SECRET", "mock_secret")
    monkeypatch.setattr(settings, "WECOM_STAFF_ID", "mock_staff_id")
    monkeypatch.setattr(settings, "WECOM_AGENT_ID", "1000001")

    # 模拟 get_token 返回 mock token
    from app.service.wecom.client import WeComClient

    async def fake_get_token(*args: object, **kwargs: object) -> str:
        return "mock_wecom_token_999"

    monkeypatch.setattr(WeComClient, "get_token", fake_get_token)

    # 2. 拦截并收集 httpx 发送的所有请求
    captured_requests: list[dict] = []

    class FakeResponse:
        def __init__(self) -> None:
            self.text = '{"errcode": 0, "errmsg": "ok"}'

    import httpx
    from unittest.mock import AsyncMock, MagicMock

    async def capture_post(url: str, *args: object, **kwargs: object) -> FakeResponse:
        captured_requests.append(
            {
                "url": url,
                "json": kwargs.get("json", {}),
                "params": kwargs.get("params", {}),
            }
        )
        return FakeResponse()

    # 整体替换 httpx.AsyncClient 工厂，避免真实连接池 __aenter__ 读取环境代理配置
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.post = AsyncMock(side_effect=capture_post)
    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=mock_client))

    # 3. 执行转人工创建
    repo = MockTransferRepo()
    mgr = TransferManager(repo)

    session_id = "session_xyz"
    user_id = "buyer_999"
    reason = "你们这个提拉米苏送过来全塌了！我要退款！"

    transfer = await mgr.request_transfer(
        session_id=session_id, user_id=user_id, reason=reason
    )

    # 验证工单创建正常
    assert transfer.session_id == session_id
    assert transfer.reason == reason

    # 验证确实发出去了两个呼叫请求：群机器人 + 应用消息推送
    assert len(captured_requests) == 2

    # 校验群机器人请求
    robot_req = [r for r in captured_requests if "webhook/send" in r["url"]][0]
    assert robot_req["json"]["msgtype"] == "markdown"
    assert session_id in robot_req["json"]["markdown"]["content"]
    assert reason in robot_req["json"]["markdown"]["content"]

    # 校验应用消息推送请求
    app_req = [r for r in captured_requests if "message/send" in r["url"]][0]
    assert app_req["json"]["touser"] == "mock_staff_id"
    assert app_req["json"]["msgtype"] == "markdown"
    assert app_req["params"]["access_token"] == "mock_wecom_token_999"
    assert session_id in app_req["json"]["markdown"]["content"]
    assert reason in app_req["json"]["markdown"]["content"]


@pytest.mark.asyncio
async def test_transfer_manager_falls_back_to_first_kf_servicer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "WECOM_ROBOT_WEBHOOK", "")
    monkeypatch.setattr(settings, "WECOM_CORP_ID", "mock_corp_id")
    monkeypatch.setattr(settings, "WECOM_SECRET", "mock_secret")
    monkeypatch.setattr(settings, "WECOM_STAFF_ID", "")
    monkeypatch.setattr(settings, "WECOM_AGENT_ID", "1000001")

    from app.service.wecom.client import WeComClient

    async def fake_get_token(*args: object, **kwargs: object) -> str:
        return "mock_wecom_token_999"

    async def fake_get_first_servicer(*args: object, **kwargs: object) -> str:
        return "servicer_001"

    monkeypatch.setattr(WeComClient, "get_token", fake_get_token)
    monkeypatch.setattr(WeComClient, "_get_first_servicer", fake_get_first_servicer)

    captured_requests: list[dict] = []

    class FakeResponse:
        text = '{"errcode": 0, "errmsg": "ok"}'

    import httpx
    from unittest.mock import AsyncMock, MagicMock

    async def capture_post(url: str, *args: object, **kwargs: object) -> FakeResponse:
        captured_requests.append(
            {
                "url": url,
                "json": kwargs.get("json", {}),
                "params": kwargs.get("params", {}),
            }
        )
        return FakeResponse()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.post = AsyncMock(side_effect=capture_post)
    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=mock_client))

    mgr = TransferManager(MockTransferRepo())
    await mgr.request_transfer(
        session_id="session-summary",
        user_id="buyer-summary",
        reason="转人工",
        summary="转人工触发：转人工\n最近对话：\n- 用户：想定4寸蛋糕",
    )

    assert len(captured_requests) == 1
    app_req = captured_requests[0]
    assert app_req["json"]["touser"] == "servicer_001"
    assert app_req["json"]["msgtype"] == "markdown"
    assert "对话摘要" in app_req["json"]["markdown"]["content"]
    assert "想定4寸蛋糕" in app_req["json"]["markdown"]["content"]
