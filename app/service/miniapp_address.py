"""小程序收货地址服务。"""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.models.miniapp_address import MiniappAddress, MiniappAddressAuditEntry
from app.repository.miniapp_address_audit_repo import MiniappAddressAuditRepo
from app.repository.miniapp_address_repo import MiniappAddressRepo

MAINLAND_PHONE_PATTERN_PREFIXES = tuple(str(prefix) for prefix in range(13, 20))


class MiniappAddressService:
    """管理小程序用户地址簿。"""

    def __init__(
        self,
        address_repo: MiniappAddressRepo,
        audit_repo: MiniappAddressAuditRepo | None = None,
    ) -> None:
        self._address_repo = address_repo
        self._audit_repo = audit_repo

    async def list_addresses(self, user_id: str) -> list[dict[str, Any]]:
        items = await self._address_repo.list_by_user(user_id)
        return [
            self._serialize(item) for item in await self._ensure_default(items, user_id)
        ]

    async def list_admin_addresses(
        self,
        *,
        page: int = 1,
        keyword: str = "",
    ) -> dict[str, Any]:
        page_size = 30
        current_page = max(1, int(page or 1))
        normalized_keyword = keyword.strip()
        items = await self._address_repo.list_admin_addresses(
            keyword=normalized_keyword,
            limit=page_size,
            offset=(current_page - 1) * page_size,
        )
        total = await self._address_repo.count_admin_addresses(
            keyword=normalized_keyword
        )
        return {
            "items": [self._serialize(item, include_user=True) for item in items],
            "total": total,
            "page": current_page,
            "pageSize": page_size,
        }

    async def get_admin_address(self, address_id: str) -> dict[str, Any]:
        item = await self._address_repo.get(address_id)
        if not item:
            raise ValueError("地址不存在")
        return {
            **self._serialize(item, include_user=True),
            "auditLogs": await self.list_admin_address_audit(address_id),
        }

    async def list_admin_address_audit(self, address_id: str) -> list[dict[str, Any]]:
        if self._audit_repo is None:
            return []
        entries = await self._audit_repo.list_by_address(address_id, limit=5)
        return [self._serialize_audit(entry) for entry in entries]

    async def save_admin_address(
        self,
        payload: dict[str, Any],
        *,
        operator: str = "admin",
    ) -> dict[str, Any]:
        user_id = str(payload.get("userId", "")).strip()
        if not user_id:
            raise ValueError("请填写用户标识")
        address_id = str(payload.get("id", "")).strip()
        existing = (
            await self._address_repo.get_for_user(address_id, user_id)
            if address_id
            else None
        )
        if address_id and not existing:
            raise ValueError("地址不存在")
        current_items = await self._address_repo.list_by_user(user_id)
        build_payload = dict(payload)
        if existing:
            build_payload["createdAt"] = existing.created_at
        item = self._build_address(
            build_payload, user_id, should_default=not current_items
        )
        if item.is_default:
            await self._address_repo.clear_default(user_id)
        await self._address_repo.upsert(item)
        action = "update" if existing else "create"
        await self._record_audit(
            action=action,
            address_id=item.id,
            user_id=user_id,
            operator=operator,
            before=self._serialize(existing, include_user=True) if existing else None,
            after=self._serialize(item, include_user=True),
            note="后台新增地址" if action == "create" else "后台编辑地址",
        )
        return self._serialize(item, include_user=True)

    async def save_address(
        self, payload: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        current_items = await self._address_repo.list_by_user(user_id)
        item = self._build_address(payload, user_id, should_default=not current_items)
        if item.is_default:
            await self._address_repo.clear_default(user_id)
        await self._address_repo.upsert(item)
        return self._serialize(item)

    async def set_default(self, address_id: str, user_id: str) -> dict[str, Any]:
        existing = await self._address_repo.get_for_user(address_id, user_id)
        if not existing:
            raise ValueError("地址不存在")
        await self._address_repo.clear_default(user_id)
        updated = await self._address_repo.set_default(address_id, user_id, self._now())
        if not updated:
            raise ValueError("地址不存在")
        return self._serialize(updated)

    async def set_admin_default(
        self,
        address_id: str,
        *,
        operator: str = "admin",
    ) -> dict[str, Any]:
        item = await self._address_repo.get(address_id)
        if not item:
            raise ValueError("地址不存在")
        before = self._serialize(item, include_user=True)
        await self._address_repo.clear_default(item.user_id)
        updated = await self._address_repo.set_default(
            address_id, item.user_id, self._now()
        )
        if not updated:
            raise ValueError("地址不存在")
        await self._record_audit(
            action="set_default",
            address_id=address_id,
            user_id=item.user_id,
            operator=operator,
            before=before,
            after=self._serialize(updated, include_user=True),
            note="后台设为默认地址",
        )
        return self._serialize(updated, include_user=True)

    async def delete_address(
        self, address_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        deleted = await self._address_repo.delete_for_user(address_id, user_id)
        if not deleted:
            raise ValueError("地址不存在")
        items = await self._address_repo.list_by_user(user_id)
        return [
            self._serialize(item) for item in await self._ensure_default(items, user_id)
        ]

    async def delete_admin_address(
        self,
        address_id: str,
        *,
        operator: str = "admin",
    ) -> dict[str, Any]:
        item = await self._address_repo.get(address_id)
        if not item:
            raise ValueError("地址不存在")
        deleted = await self._address_repo.delete_for_user(address_id, item.user_id)
        if not deleted:
            raise ValueError("地址不存在")
        await self._ensure_default(
            await self._address_repo.list_by_user(item.user_id), item.user_id
        )
        await self._record_audit(
            action="delete",
            address_id=address_id,
            user_id=item.user_id,
            operator=operator,
            before=self._serialize(deleted, include_user=True),
            after=None,
            note="后台删除地址",
        )
        return self._serialize(deleted, include_user=True)

    def _build_address(
        self,
        payload: dict[str, Any],
        user_id: str,
        *,
        should_default: bool,
    ) -> MiniappAddress:
        address_id = str(payload.get("id") or f"addr_{uuid4().hex[:16]}")
        receiver_name = str(payload.get("receiverName", "")).strip()
        receiver_phone = str(payload.get("receiverPhone", "")).strip()
        address = str(payload.get("address", "")).strip()
        self._validate(receiver_name, receiver_phone, address)
        now = self._now()
        return MiniappAddress(
            id=address_id,
            user_id=user_id,
            receiver_name=receiver_name,
            receiver_phone=receiver_phone,
            address=address,
            is_default=1 if bool(payload.get("isDefault")) or should_default else 0,
            created_at=str(payload.get("createdAt") or now),
            updated_at=now,
        )

    def _validate(self, receiver_name: str, receiver_phone: str, address: str) -> None:
        if not receiver_name:
            raise ValueError("请填写联系人")
        if (
            len(receiver_phone) != 11
            or not receiver_phone.isdigit()
            or receiver_phone[:2] not in MAINLAND_PHONE_PATTERN_PREFIXES
        ):
            raise ValueError("请填写正确的 11 位手机号")
        if not address:
            raise ValueError("请填写收货地址")

    async def _ensure_default(
        self,
        items: list[MiniappAddress],
        user_id: str,
    ) -> list[MiniappAddress]:
        if not items:
            return []
        default_count = sum(1 for item in items if item.is_default)
        if default_count == 1:
            return items
        default_item = items[0]
        await self._address_repo.clear_default(user_id)
        updated_default = await self._address_repo.set_default(
            default_item.id, user_id, self._now()
        )
        if updated_default:
            return await self._address_repo.list_by_user(user_id)
        return items

    def _serialize(
        self, item: MiniappAddress, *, include_user: bool = False
    ) -> dict[str, Any]:
        payload = {
            "id": item.id,
            "receiverName": item.receiver_name,
            "receiverPhone": item.receiver_phone,
            "address": item.address,
            "isDefault": bool(item.is_default),
            "createdAt": item.created_at,
            "updatedAt": item.updated_at,
        }
        if include_user:
            payload["userId"] = item.user_id
        return payload

    async def _record_audit(
        self,
        *,
        action: str,
        address_id: str,
        user_id: str,
        operator: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        note: str,
    ) -> None:
        if self._audit_repo is None:
            return
        await self._audit_repo.add(
            MiniappAddressAuditEntry(
                address_id=address_id,
                user_id=user_id,
                operator=operator or "admin",
                action=action,
                before_json=json.dumps(before or {}, ensure_ascii=False),
                after_json=json.dumps(after or {}, ensure_ascii=False),
                note=note,
                created_at=self._now(),
            )
        )

    def _serialize_audit(self, entry: MiniappAddressAuditEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "addressId": entry.address_id,
            "userId": entry.user_id,
            "operator": entry.operator,
            "action": entry.action,
            "before": self._loads_dict(entry.before_json),
            "after": self._loads_dict(entry.after_json),
            "note": entry.note,
            "createdAt": entry.created_at,
        }

    def _loads_dict(self, raw: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
