"""
店铺配置数据访问层。

基于 shop_config 键值表，支持读写任意配置项。
"""

import json

import aiosqlite


class ConfigRepo:
    """店铺配置仓库：键值读写。"""

    def __init__(self, db: aiosqlite.Connection = None) -> None:
        self._injected_db = db

    @property
    def _db(self) -> aiosqlite.Connection:
        if self._injected_db is not None:
            return self._injected_db
        try:
            from app.database import db_conn_var
            return db_conn_var.get()
        except LookupError as exc:
            raise RuntimeError("数据库操作未在 db_session_scope 上下文管理器中执行！") from exc

    async def get(self, key: str) -> str | None:
        """读取配置项，不存在返回 None。"""
        rows = await self._db.execute_fetchall(
            "SELECT value FROM shop_config WHERE key = ?",
            (key,),
        )
        return rows[0]["value"] if rows else None

    async def set(self, key: str, value: str) -> None:
        """写入配置项，已存在则覆盖。"""
        await self._db.execute(
            "INSERT INTO shop_config(key, value, updated_at) VALUES(?, ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (key, value),
        )
        await self._db.commit()

    async def get_list(self, key: str) -> list[str]:
        """读取 JSON 数组配置项，不存在或解析失败返回空列表。"""
        raw = await self.get(key)
        if not raw:
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []

    async def set_list(self, key: str, items: list[str]) -> None:
        """将字符串列表序列化为 JSON 后写入配置。"""
        await self.set(key, json.dumps(items, ensure_ascii=False))
