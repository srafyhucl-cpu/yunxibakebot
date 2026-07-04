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


def test_evaluate_reply_requires_all_semantic_terms() -> None:
    probe = callback_check.CallbackProbe(
        "stock",
        "帮我看看伯牙绝弦库存",
        required_all_terms=("库存", "72"),
    )

    missing_number = callback_check.evaluate_reply(
        probe,
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "伯牙绝弦库存请以小程序为准。",
            },
        },
        5,
    )
    matched = callback_check.evaluate_reply(
        probe,
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "伯牙绝弦库存显示72份。",
            },
        },
        5,
    )

    assert missing_number.passed is False
    assert matched.passed is True


def test_evaluate_reply_rejects_revenue_empty_detour() -> None:
    probe = callback_check.CallbackProbe(
        "today-revenue-summary",
        "今天营业额多少",
        required_any_terms=("元", "营业额", "销售额"),
        forbidden_terms=("未找到", "暂无数据", "后台订单页核对"),
    )

    result = callback_check.evaluate_reply(
        probe,
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "未找到今日营业额数据，请进入后台订单页核对日期范围。",
            },
        },
        5,
    )

    assert result.passed is False
    assert result.semantic_safe is False


def test_evaluate_reply_rejects_wrong_fulfillment_pressure() -> None:
    probe = callback_check.CallbackProbe(
        "casual-fulfillment-pressure",
        "今天发货压力大不大",
        required_all_terms=("发货压力",),
        required_any_terms=("偏高", "中等", "低"),
        forbidden_terms=("压力不大",),
    )

    result = callback_check.evaluate_reply(
        probe,
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "今天发货压力不大，目前仅5单待处理。",
            },
        },
        5,
    )

    assert result.passed is False
    assert result.semantic_safe is False


def test_evaluate_reply_rejects_product_knowledge_miss() -> None:
    probe = callback_check.CallbackProbe(
        "product-stock-recommend-replacement",
        "伯牙绝弦库存不够怎么推荐替代",
        required_all_terms=("库存", "72"),
        required_any_terms=("推荐", "替代", "客户", "回复"),
        forbidden_terms=("未找到匹配知识",),
    )

    result = callback_check.evaluate_reply(
        probe,
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "伯牙绝弦｜258.00元｜库存 72｜生日蛋糕\n未找到匹配知识。",
            },
        },
        5,
    )

    assert result.passed is False
    assert result.semantic_safe is False


def test_evaluate_reply_rejects_empty_order_generic_detour() -> None:
    probe = callback_check.CallbackProbe(
        "evening-pending-orders",
        "晚上还有哪些待处理订单",
        required_any_terms=("待处理", "约送", "晚上", "待发货", "待收货"),
        forbidden_terms=("换商品名", "时间范围再查"),
    )

    result = callback_check.evaluate_reply(
        probe,
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "没有查到待处理订单。建议换商品名、状态或时间范围再查。",
            },
        },
        5,
    )

    assert result.passed is False
    assert result.semantic_safe is False


def test_evaluate_reply_rejects_markdown_decorations() -> None:
    result = callback_check.evaluate_reply(
        callback_check.CallbackProbe("plain-text", "今天哪个商品卖得多"),
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": "今日销量第一：**巧克力樱桃炸弹**。",
            },
        },
        5,
    )

    assert result.passed is False
    assert result.semantic_safe is False
    assert "semantic" in result.detail


def test_evaluate_reply_rejects_ump_marker_in_handoff_summary() -> None:
    result = callback_check.evaluate_reply(
        callback_check.CallbackProbe(
            "handoff-pending",
            "现在有哪些待人工",
            required_any_terms=("待人工", "转人工"),
            forbidden_terms=("UMP", "type=card", "%E5%"),
        ),
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": (
                    "工单尾号 77f40｜转人工｜摘要：AI：好的 "
                    "[UMP: type=card&id=1&title=%E5%B0%8F]"
                ),
            },
        },
        5,
    )

    assert result.passed is False
    assert result.semantic_safe is False
    assert "semantic" in result.detail


def test_evaluate_reply_rejects_raw_offline_review_skip_marker() -> None:
    result = callback_check.evaluate_reply(
        callback_check.CallbackProbe(
            "offline-review-summary",
            "昨晚离线复盘结果",
            required_any_terms=("离线复盘", "复盘"),
            forbidden_terms=("outside_night_window", "skippedReason"),
        ),
        200,
        {
            "msgtype": "stream",
            "stream": {
                "id": "msg",
                "finish": True,
                "content": (
                    "最近一轮离线复盘未执行：outside_night_window。\n"
                    "下一步：如果 skippedReason 不为空，先确认夜间窗口。"
                ),
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
    if "伯牙绝弦" in content and ("替代" in content or "怎么跟客户说" in content):
        return "伯牙绝弦当前库存72，建议给客户回复可推荐替代款。"
    if "怎么跟客户说" in content:
        return "当前待发货订单已汇总，并给出可复制给客户的回复。"
    if "怎么回复客户" in content and ("退款" in content or "售后" in content):
        return "退款订单已汇总，并给出售后回复客户的话术。"
    if "要盯" in content or "需要注意" in content or "待办" in content:
        return (
            "今日订单优先级和发货压力已汇总，包含待处理、履约风险、退款和无物流事项。"
        )
    if "快超时" in content or "发货压力" in content or "履约压力" in content:
        return "发货压力：偏高。待发货履约风险已汇总，含约送时间和订单尾号。"
    if "晚上" in content and "待处理" in content:
        return "晚上待处理订单已汇总，包含约送时间和待发货状态。"
    if "明天" in content and "待处理" in content:
        return "明天待处理订单已汇总，包含约送时间和待发货状态。"
    if "后天" in content and "待处理" in content:
        return "后天待处理订单已汇总，包含约送时间和待发货状态。"
    if "周末" in content and "待处理" in content:
        return "周末待处理订单已汇总，包含约送时间和待发货状态。"
    if "下周一" in content and "待处理" in content:
        return "下周一待处理订单已汇总，包含约送时间和待发货状态。"
    if "没发货" in content or "没处理" in content:
        return "当前待发货订单已汇总。"
    if "物流" in content:
        return "当前暂无物流订单已汇总。"
    if "哪个商品" in content or "卖爆" in content:
        return "今日销量排行已汇总。"
    if "营业额" in content or "销售额" in content:
        return "销售额已汇总，共206.50元。"
    if "退款" in content or "退单" in content or "售后订单" in content:
        return "退款订单已汇总，共1单，合计88.00元。"
    if "伯牙绝弦" in content and ("库存" in content or "还有吗" in content):
        return "伯牙绝弦当前库存72，售价258元。"
    if "库存" in content or "还有吗" in content:
        return "商品库存已汇总。"
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
