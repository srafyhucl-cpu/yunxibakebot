"""远程 URL SSRF 和响应边界合同测试。"""

import pytest

from app.service.security.url_policy import UnsafeRemoteUrl, validate_remote_url


@pytest.mark.asyncio
async def test_url_policy_rejects_private_resolution(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.service.security.url_policy._resolve_addresses",
        lambda _hostname, _port: {"127.0.0.1"},
    )

    with pytest.raises(UnsafeRemoteUrl):
        await validate_remote_url("https://img.example/file.jpg", ["img.example"])


@pytest.mark.asyncio
async def test_url_policy_rejects_host_outside_allowlist(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.service.security.url_policy._resolve_addresses",
        lambda _hostname, _port: {"93.184.216.34"},
    )

    with pytest.raises(UnsafeRemoteUrl):
        await validate_remote_url("https://attacker.example/file.jpg", ["img.example"])
