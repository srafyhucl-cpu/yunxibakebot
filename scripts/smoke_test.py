"""上线前只读冒烟检查。"""

import asyncio
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import settings  # noqa: E402

HTTP_OK = 200
REQUEST_TIMEOUT_SECONDS = 5
MIN_KNOWLEDGE_ROWS = 1
HEALTH_STATUS_OK = "ok"
HEALTH_PATH = "/health"


@dataclass(frozen=True)
class SmokeResult:
    name: str
    passed: bool
    detail: str = ""


EXPECTED_TABLES: tuple[str, ...] = (
    "sessions",
    "messages",
    "knowledge_base",
    "human_transfers",
    "orders",
    "shop_config",
)


def check_env_file() -> SmokeResult:
    env_path = ROOT_DIR / ".env"
    return SmokeResult(".env 文件存在", env_path.exists(), str(env_path))


def check_database_file() -> SmokeResult:
    db_path = ROOT_DIR / settings.DB_PATH
    return SmokeResult("数据库文件存在", db_path.exists(), str(db_path))


def get_existing_tables(conn: sqlite3.Connection) -> set[str]:
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = ? AND name IN "
        "(?, ?, ?, ?, ?, ?) ORDER BY name ASC",
        ("table", *EXPECTED_TABLES),
    )
    return {row[0] for row in cursor.fetchall()}


def check_schema() -> SmokeResult:
    db_path = ROOT_DIR / settings.DB_PATH
    if not db_path.exists():
        return SmokeResult("数据库表结构", False, "数据库文件不存在")
    with sqlite3.connect(db_path) as conn:
        existing_tables = get_existing_tables(conn)
    missing_tables = sorted(set(EXPECTED_TABLES) - existing_tables)
    detail = "缺失表: " + ", ".join(missing_tables) if missing_tables else "关键表已存在"
    return SmokeResult("数据库表结构", not missing_tables, detail)


def check_knowledge_rows() -> SmokeResult:
    db_path = ROOT_DIR / settings.DB_PATH
    if not db_path.exists():
        return SmokeResult("知识库数据", False, "数据库文件不存在")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(id) FROM knowledge_base WHERE is_active = ?", (1,))
        row_count = int(cursor.fetchone()[0])
    is_enough = row_count >= MIN_KNOWLEDGE_ROWS
    return SmokeResult("知识库数据", is_enough, f"active rows={row_count}")


def check_embedding_file() -> SmokeResult:
    embedding_path = ROOT_DIR / settings.EMBEDDING_PATH
    return SmokeResult("向量索引文件", embedding_path.exists(), str(embedding_path))


def check_required_settings() -> SmokeResult:
    missing_names: list[str] = []
    if not settings.ADMIN_API_TOKEN:
        missing_names.append("ADMIN_API_TOKEN")
    if not settings.DEEPSEEK_API_KEY:
        missing_names.append("DEEPSEEK_API_KEY")
    detail = "缺失: " + ", ".join(missing_names) if missing_names else "关键配置已设置"
    return SmokeResult("关键环境变量", not missing_names, detail)


async def check_health_endpoint() -> SmokeResult:
    url = f"http://{settings.SERVER_HOST}:{settings.SERVER_PORT}{HEALTH_PATH}"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        return SmokeResult("健康检查接口", False, f"请求失败: {exc}")
    if response.status_code != HTTP_OK:
        return SmokeResult("健康检查接口", False, f"status={response.status_code}")
    payload = response.json()
    is_ok = payload.get("status") == HEALTH_STATUS_OK
    return SmokeResult("健康检查接口", is_ok, str(payload))


def run_static_checks() -> list[SmokeResult]:
    return [
        check_env_file(),
        check_database_file(),
        check_schema(),
        check_knowledge_rows(),
        check_embedding_file(),
        check_required_settings(),
    ]


def print_results(results: list[SmokeResult]) -> None:
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}: {result.detail}")


async def main() -> int:
    results = run_static_checks()
    results.append(await check_health_endpoint())
    print_results(results)
    failed_results = [result for result in results if not result.passed]
    return 1 if failed_results else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
