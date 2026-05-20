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

    async def create(self, session_id: str, user_id: str, reason: str = "", summary: str = "") -> HumanTransfer:
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


@pytest.mark.asyncio
async def test_transfer_manager_emergency_notification_triggers_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试当触发 request_transfer 判定为转人工时，紧急呼叫通知中心被完美触发。"""
    # 1. 模拟企微配置
    monkeypatch.setattr(settings, "WECOM_ROBOT_WEBHOOK", "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=mock_key")
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
    captured_requests = []

    class FakeResponse:
        def __init__(self) -> None:
            self.text = "{\"errcode\": 0, \"errmsg\": \"ok\"}"

    async def fake_post(self, url: str, *args: object, **kwargs: object) -> FakeResponse:
        json_data = kwargs.get("json", {})
        captured_requests.append({
            "url": url,
            "json": json_data,
            "params": kwargs.get("params", {})
        })
        return FakeResponse()

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    # 3. 执行转人工创建
    repo = MockTransferRepo()
    mgr = TransferManager(repo)

    session_id = "session_xyz"
    user_id = "buyer_999"
    reason = "你们这个提拉米苏送过来全塌了！我要退款！"

    transfer = await mgr.request_transfer(session_id=session_id, user_id=user_id, reason=reason)

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
