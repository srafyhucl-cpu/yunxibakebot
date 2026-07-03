import json

from app.service.wecom.crypto import decrypt, encrypt, generate_signature
from scripts import check_wecom_employee_agent_callback as callback_check
from scripts.wecom_employee_agent_probe_cases import default_probe_cases


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, object]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload, ensure_ascii=False)

    def json(self) -> dict[str, object]:
        return self._payload


class _FakeAsyncClient:
    requested_payloads: list[dict[str, object] | None] = []
    requested_params: list[dict[str, str] | None] = []

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def post(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> _FakeResponse:
        self.requested_params.append(params)
        self.requested_payloads.append(json)
        assert url.endswith("/api/v1/wecom/intelligent-bot/callback")
        msg_encrypt = str((json or {}).get("encrypt") or "")
        plaintext = decrypt(callback_check.TEST_AES_KEY, msg_encrypt)
        message = __import__("json").loads(plaintext)
        content = message["text"]["content"]
        reply_text = _fake_reply_text(content)
        reply_encrypt = encrypt(
            callback_check.TEST_AES_KEY,
            __import__("json").dumps(
                {
                    "msgtype": "stream",
                    "stream": {
                        "id": message["msgid"],
                        "finish": True,
                        "content": reply_text,
                    },
                },
                ensure_ascii=False,
            ),
            "",
        )
        timestamp = "1783000001"
        nonce = "reply-nonce"
        return _FakeResponse(
            200,
            {
                "encrypt": reply_encrypt,
                "msgsignature": generate_signature(
                    callback_check.TEST_TOKEN,
                    timestamp,
                    nonce,
                    reply_encrypt,
                ),
                "timestamp": timestamp,
                "nonce": nonce,
            },
        )


def test_parse_base_url_rejects_path() -> None:
    try:
        callback_check.parse_base_url("https://yunxifood.cn/ready")
    except ValueError as exc:
        assert "根地址" in str(exc)
    else:
        raise AssertionError("base url with path should be rejected")


async def test_run_callback_checks_covers_employee_queries(monkeypatch) -> None:
    _FakeAsyncClient.requested_payloads = []
    _FakeAsyncClient.requested_params = []
    monkeypatch.setattr(callback_check.httpx, "AsyncClient", _FakeAsyncClient)

    results = await callback_check.run_callback_checks(
        "https://yunxifood.cn",
        callback_check.CallbackCredentials(
            token=callback_check.TEST_TOKEN,
            encoding_aes_key=callback_check.TEST_AES_KEY,
        ),
    )
    report = callback_check.build_json_report("https://yunxifood.cn", results)
    serialized = json.dumps(report, ensure_ascii=False)
    expected_cases = default_probe_cases(__import__("datetime").date.today())

    assert report["status"] == "passed"
    assert report["total"] == len(expected_cases)
    assert report["failed"] == 0
    assert {result.name for result in results} == {case.name for case in expected_cases}
    assert callback_check.TEST_TOKEN not in serialized
    assert callback_check.TEST_AES_KEY not in serialized
    assert "encrypt" not in serialized
    assert all(result.reply_valid for result in results)
    assert all(result.privacy_safe for result in results)


def test_evaluate_reply_rejects_privacy_leak() -> None:
    result = callback_check.evaluate_reply(
        callback_check.CallbackProbe("privacy", "查订单"),
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "手机号 13812345678，完整订单号 E202607031234567890",
            },
        },
        5,
    )

    assert result.passed is False
    assert result.reply_valid is True
    assert result.privacy_safe is False
    assert "privacy" in result.detail


def test_evaluate_reply_rejects_buyer_id_hint() -> None:
    result = callback_check.evaluate_reply(
        callback_check.CallbackProbe("privacy", "现在有哪些待人工"),
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "当前有5笔待人工订单，来自同一买家（ID: wmLg...ismA）。",
            },
        },
        5,
    )

    assert result.passed is False
    assert result.privacy_safe is False


def test_evaluate_reply_rejects_full_uuid() -> None:
    result = callback_check.evaluate_reply(
        callback_check.CallbackProbe("privacy", "现在有哪些待人工"),
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "da8f723e-d755-4868-8c48-bf9813a77f40｜转人工",
            },
        },
        5,
    )

    assert result.passed is False
    assert result.privacy_safe is False


def test_evaluate_reply_rejects_delivery_order_tail_detour() -> None:
    result = callback_check.evaluate_reply(
        callback_check.CallbackProbe(
            "delivery-knowledge",
            "明天能配送吗",
            required_any_terms=("配送",),
            forbidden_terms=("订单尾号", "订单状态"),
        ),
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "请提供订单尾号，我帮您查一下配送安排。如需确认，也可登录后台查看订单状态。",
            },
        },
        5,
    )

    assert result.passed is False
    assert result.semantic_safe is False
    assert "semantic" in result.detail


async def test_main_requires_callback_credentials(monkeypatch, capsys) -> None:
    monkeypatch.setattr(callback_check, "resolve_callback_credentials", lambda: None)

    exit_code = await callback_check.main(["--json"])

    assert exit_code == 2
    assert "WECOM_INTELLIGENT_BOT_TOKEN" in capsys.readouterr().err


async def test_main_json_output_can_be_written_to_file(monkeypatch, tmp_path) -> None:
    async def fake_run_callback_checks(base_url, credentials):
        return [
            callback_check.CallbackProbeResult(
                name="ok",
                query="今天一共多少订单",
                status_code=200,
                passed=True,
                reply_valid=True,
                privacy_safe=True,
                semantic_safe=True,
                elapsed_ms=1,
                content_preview="员工回复",
            )
        ]

    monkeypatch.setattr(
        callback_check,
        "resolve_callback_credentials",
        lambda: callback_check.CallbackCredentials("token", "aes"),
    )
    monkeypatch.setattr(callback_check, "run_callback_checks", fake_run_callback_checks)
    report_path = tmp_path / "reports" / "employee-agent-callback.json"

    exit_code = await callback_check.main(["--json", "--output", str(report_path)])

    assert exit_code == 0
    assert report_path.read_bytes().startswith(callback_check.UTF8_BOM)
    payload = json.loads(report_path.read_text(encoding="utf-8-sig"))
    assert payload["status"] == "passed"
    assert payload["results"][0]["content_preview"] == "员工回复"


def _fake_reply_text(content: str) -> str:
    if "没发货" in content or "没处理" in content:
        return "当前待发货订单已汇总。"
    if "物流" in content:
        return "当前暂无物流订单已汇总。"
    if "哪个商品" in content or "卖爆" in content:
        return "今日销量排行已汇总。"
    if "库存" in content or "还有吗" in content:
        return "库存已汇总。"
    if "配送" in content:
        return "配送规则请按后台知识库确认。"
    if "异常" in content or "稳不稳" in content:
        return "系统状态已汇总。"
    if "待人工" in content or "人接" in content:
        return "当前待人工事项已汇总。"
    if "地址线索" in content:
        return "客户地址线索已汇总。"
    if "campaign" in content:
        return "群活动 campaign 已汇总。"
    if "离线复盘" in content:
        return "昨晚离线复盘结果已汇总。"
    return "今日订单共1单。"
