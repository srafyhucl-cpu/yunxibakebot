"""容器运行时边界合同测试。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_docker_runtime_is_non_root_and_single_worker() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    digest = "sha256:f5cf0344c9886ff24d34797578d5d7dd6e8911ae0fe5962bb55d0f89603ec361"
    assert f"FROM python:3.11-slim-bookworm@{digest} AS builder" in dockerfile
    assert f"FROM python:3.11-slim-bookworm@{digest} AS runtime" in dockerfile
    assert "pip install --no-cache-dir -r requirements-dev.txt" not in dockerfile
    assert "https://download.pytorch.org/whl/cpu" in dockerfile
    assert "torch==2.12.0+cpu" in dockerfile
    assert "--no-index --find-links /wheels" in dockerfile
    assert "pip uninstall --yes wheel jaraco.context" in dockerfile
    assert "USER yunxi" in dockerfile
    assert '"--workers", "1"' in dockerfile
    assert "SentenceTransformer" not in dockerfile
    assert "DB_PATH=/app/data/bot.db" in compose
    assert "/ready" in dockerfile
    assert "/ready" in compose
    assert "reports/" in dockerignore
    assert "web/admin/node_modules/" in dockerignore
    assert "web/admin/dist/" not in dockerignore
