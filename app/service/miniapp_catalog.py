"""小程序商品目录服务。"""

from dataclasses import dataclass
import json
from urllib.parse import urlparse

from httpx import AsyncClient, HTTPError

from app.models.config import FEATURED_PRODUCTS_KEY
from app.models.knowledge import KnowledgeCategory, KnowledgeEntry
from app.repository.config_repo import ConfigRepo
from app.repository.knowledge_product_repo import KnowledgeProductRepo
from app.repository.knowledge_repo import KnowledgeRepo
from app.repository.youzan_repo import YouzanProductRepo

DEFAULT_PRODUCT_LIMIT = 50
MAX_IDS_QUERY = 50
FALLBACK_CATEGORY_ID = "youzan-products"
DEFAULT_PRODUCT_NOTICE = "手工现制商品，请下单前确认取货或配送时间。"
IMAGE_PROXY_PATH_TEMPLATE = "/api/v1/miniapp/products/{product_id}/image"
IMAGE_FETCH_TIMEOUT_SECONDS = 8.0
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_SCHEMES = {"http", "https"}


@dataclass(frozen=True)
class ProductImagePayload:
    """商品图片代理返回体。"""

    content: bytes
    content_type: str


class MiniappCatalogService:
    """为小程序提供公开商品列表和详情。"""

    def __init__(
        self,
        product_repo: KnowledgeProductRepo,
        knowledge_repo: KnowledgeRepo,
        config_repo: ConfigRepo,
        youzan_product_repo: YouzanProductRepo | None = None,
    ) -> None:
        self._product_repo = product_repo
        self._knowledge_repo = knowledge_repo
        self._config_repo = config_repo
        self._youzan_product_repo = youzan_product_repo

    async def list_products(
        self,
        *,
        ids: str = "",
        category_id: str = "",
        featured: bool = False,
    ) -> list[dict]:
        """按装修货架、分类或推荐位返回小程序商品。"""
        if ids.strip():
            return await self._list_products_by_ids(ids)

        featured_titles = await self._get_featured_titles(featured)
        if category_id.startswith("youzan-") and self._youzan_product_repo is not None:
            entries = await self._list_entries_by_youzan_category(category_id)
            if entries:
                return [
                    await self._serialize_product(
                        entry, preferred_category_id=category_id
                    )
                    for entry in entries
                ]

        entries = await self._product_repo.get_all_products(
            search=category_id,
            limit=DEFAULT_PRODUCT_LIMIT,
            is_active=1,
            featured_titles=featured_titles,
        )
        if featured_titles is not None:
            entries = self._sort_entries_by_titles(entries, featured_titles)
        return [await self._serialize_product(entry) for entry in entries]

    async def list_categories(self) -> list[dict]:
        """返回小程序公开商品分类。"""
        if self._youzan_product_repo is None:
            return []
        categories = await self._youzan_product_repo.list_public_categories()
        return [
            {
                "id": self._build_youzan_category_id(str(category["tag_id"])),
                "title": category["title"],
                "sort": int(category["sort"] or 0),
                "productCount": int(category["product_count"] or 0),
            }
            for category in categories
        ]

    async def get_product(self, product_id: str) -> dict | None:
        """读取小程序商品详情，优先使用有赞商品 ID。"""
        entry = await self._get_product_entry(product_id)
        if entry is None:
            return None
        return await self._serialize_product(entry)

    async def fetch_product_image(self, product_id: str) -> ProductImagePayload | None:
        """通过商品 ID 受控拉取原始商品图，避免小程序直连第三方图片域名。"""
        entry = await self._get_product_entry(product_id)
        if entry is None:
            return None

        image_url = str(getattr(entry, "image_url", "") or "").strip()
        if not self._is_allowed_image_url(image_url):
            return None

        try:
            async with AsyncClient(
                timeout=IMAGE_FETCH_TIMEOUT_SECONDS, follow_redirects=True
            ) as client:
                response = await client.get(image_url)
        except HTTPError:
            return None

        if response.status_code != 200:
            return None

        content_type = (
            response.headers.get("content-type", "").split(";")[0].strip().lower()
        )
        if not content_type.startswith("image/"):
            return None

        content_length = response.headers.get("content-length", "")
        if content_length.isdigit() and int(content_length) > MAX_IMAGE_BYTES:
            return None

        content = response.content
        if not content or len(content) > MAX_IMAGE_BYTES:
            return None
        return ProductImagePayload(content=content, content_type=content_type)

    async def _list_products_by_ids(self, ids: str) -> list[dict]:
        products: list[dict] = []
        seen_ids: set[str] = set()
        product_ids = [item.strip() for item in ids.split(",") if item.strip()]
        for product_id in product_ids[:MAX_IDS_QUERY]:
            product = await self.get_product(product_id)
            if product is None or product["id"] in seen_ids:
                continue
            products.append(product)
            seen_ids.add(product["id"])
        return products

    async def _get_by_youzan_item_id(self, product_id: str) -> dict | None:
        entry = await self._get_entry_by_youzan_item_id(product_id)
        return await self._serialize_product(entry) if entry is not None else None

    async def _list_entries_by_youzan_category(
        self, category_id: str
    ) -> list[KnowledgeEntry]:
        if self._youzan_product_repo is None:
            return []
        category_key = self._parse_youzan_category_id(category_id)
        products = await self._youzan_product_repo.list_products_by_category_key(
            category_key,
            limit=DEFAULT_PRODUCT_LIMIT,
        )
        entries: list[KnowledgeEntry] = []
        for product in products:
            entry = await self._get_entry_by_youzan_item_id(str(product["item_id"]))
            if entry is not None:
                entries.append(entry)
        return entries

    async def _get_product_entry(self, product_id: str) -> KnowledgeEntry | None:
        normalized_id = product_id.strip()
        if not normalized_id:
            return None

        entry = await self._get_entry_by_youzan_item_id(normalized_id)
        if entry is not None:
            return entry

        if not normalized_id.isdigit():
            return None

        entry = await self._knowledge_repo.get_by_id(int(normalized_id))
        if not self._is_sellable_product_entry(entry):
            return None
        if entry.youzan_item_id:
            youzan_entry = await self._get_entry_by_youzan_item_id(entry.youzan_item_id)
            if youzan_entry is not None:
                return youzan_entry
        return entry

    async def _get_entry_by_youzan_item_id(
        self, product_id: str
    ) -> KnowledgeEntry | None:
        entries = await self._product_repo.get_all_products(
            limit=1,
            is_active=1,
            youzan_item_id_filter=product_id,
        )
        return entries[0] if entries else None

    async def _get_featured_titles(self, featured: bool) -> list[str] | None:
        if not featured:
            return None
        return await self._config_repo.get_list(FEATURED_PRODUCTS_KEY)

    async def _serialize_product(
        self,
        entry: KnowledgeEntry,
        *,
        preferred_category_id: str = "",
    ) -> dict:
        tags = self._split_tags(entry.keywords)
        sold_num = int(getattr(entry, "sold_num", 0) or 0)
        stock = int(getattr(entry, "stock", 0) or 0)
        category = await self._get_entry_category(entry, tags, preferred_category_id)
        return {
            "id": str(entry.youzan_item_id or entry.id),
            "title": entry.title,
            "subtitle": self._build_subtitle(entry.content),
            "imageUrl": self._build_image_proxy_url(entry),
            "priceFen": int(getattr(entry, "price_fen", 0) or 0),
            "soldText": self._build_sold_text(sold_num, stock),
            "categoryId": category["id"],
            "categoryName": category["title"],
            "stock": stock,
            "isActive": bool(entry.is_active),
            "tags": tags,
            "description": entry.content,
            "specs": tags,
            "notices": [DEFAULT_PRODUCT_NOTICE],
        }

    def _build_subtitle(self, content: str) -> str:
        compact_content = " ".join((content or "").split())
        if len(compact_content) <= 36:
            return compact_content
        return f"{compact_content[:36]}..."

    def _build_sold_text(self, sold_num: int, stock: int) -> str:
        if sold_num > 0:
            return f"已售 {sold_num}"
        if stock > 0:
            return "库存充足"
        return "可咨询客服"

    def _infer_category_id(self, tags: list[str]) -> str:
        return tags[0] if tags else FALLBACK_CATEGORY_ID

    async def _get_entry_category(
        self,
        entry: KnowledgeEntry,
        tags: list[str],
        preferred_category_id: str = "",
    ) -> dict:
        classification_ids = self._extract_json_ids(entry, "classification_ids_json")
        if classification_ids and self._youzan_product_repo is not None:
            preferred_key = self._parse_youzan_category_id(preferred_category_id)
            preferred_classification_id = preferred_key.replace(
                "classification-", "", 1
            )
            ordered_ids = (
                [preferred_classification_id]
                if preferred_classification_id in classification_ids
                else []
            )
            ordered_ids.extend(
                item for item in classification_ids if item not in ordered_ids
            )
            for classification_id in ordered_ids:
                category_key = f"classification-{classification_id}"
                category = await self._youzan_product_repo.get_category(category_key)
                if category is not None and int(category.get("is_public", 0) or 0) == 1:
                    return {
                        "id": self._build_youzan_category_id(category_key),
                        "title": str(category["title"]),
                    }
        tag_ids = self._extract_tag_ids(entry)
        if tag_ids and self._youzan_product_repo is not None:
            preferred_tag_id = preferred_category_id.replace("youzan-tag-", "", 1)
            ordered_tag_ids = [preferred_tag_id] if preferred_tag_id in tag_ids else []
            ordered_tag_ids.extend(
                tag_id for tag_id in tag_ids if tag_id not in ordered_tag_ids
            )
            tag_id = ""
            category = None
            for candidate_tag_id in ordered_tag_ids:
                candidate_category = await self._youzan_product_repo.get_category(
                    candidate_tag_id
                )
                if (
                    candidate_category is not None
                    and int(candidate_category.get("is_public", 0) or 0) == 1
                ):
                    tag_id = candidate_tag_id
                    category = candidate_category
                    break
            if not tag_id:
                fallback_id = self._infer_category_id(tags)
                return {"id": fallback_id, "title": fallback_id}
            if category is not None:
                return {
                    "id": self._build_youzan_category_id(str(category["tag_id"])),
                    "title": str(category["title"]),
                }
        fallback_id = self._infer_category_id(tags)
        return {"id": fallback_id, "title": fallback_id}

    def _extract_tag_ids(self, entry: KnowledgeEntry) -> list[str]:
        return self._extract_json_ids(entry, "tag_ids_json")

    def _extract_json_ids(self, entry: KnowledgeEntry, attr_name: str) -> list[str]:
        raw_value = str(getattr(entry, attr_name, "") or "[]")
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            return []
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    def _build_youzan_category_id(self, tag_id: str) -> str:
        if tag_id.startswith("classification-"):
            return tag_id.replace("classification-", "youzan-classification-", 1)
        if tag_id.startswith("group-"):
            return tag_id.replace("group-", "youzan-group-", 1)
        if tag_id.startswith("second-group-"):
            return tag_id.replace("second-group-", "youzan-second-group-", 1)
        if tag_id.startswith("leaf-category-"):
            return tag_id.replace("leaf-category-", "youzan-leaf-category-", 1)
        return f"youzan-tag-{tag_id}"

    def _parse_youzan_category_id(self, category_id: str) -> str:
        if category_id.startswith("youzan-classification-"):
            return category_id.replace("youzan-classification-", "classification-", 1)
        if category_id.startswith("youzan-group-"):
            return category_id.replace("youzan-group-", "group-", 1)
        if category_id.startswith("youzan-second-group-"):
            return category_id.replace("youzan-second-group-", "second-group-", 1)
        if category_id.startswith("youzan-leaf-category-"):
            return category_id.replace("youzan-leaf-category-", "leaf-category-", 1)
        return category_id.replace("youzan-tag-", "", 1)

    def _split_tags(self, keywords: str) -> list[str]:
        normalized = keywords.replace("，", ",").replace("、", ",").replace(" ", ",")
        return [item.strip() for item in normalized.split(",") if item.strip()]

    def _build_image_proxy_url(self, entry: KnowledgeEntry) -> str:
        if not str(getattr(entry, "image_url", "") or "").strip():
            return ""
        product_id = str(entry.youzan_item_id or entry.id)
        return IMAGE_PROXY_PATH_TEMPLATE.format(product_id=product_id)

    def _is_allowed_image_url(self, image_url: str) -> bool:
        if not image_url:
            return False
        parsed = urlparse(image_url)
        return parsed.scheme in ALLOWED_IMAGE_SCHEMES and bool(parsed.netloc)

    def _is_sellable_product_entry(self, entry: KnowledgeEntry | None) -> bool:
        if entry is None:
            return False
        return entry.category == KnowledgeCategory.PRODUCT and bool(entry.is_active)

    def _sort_entries_by_titles(
        self,
        entries: list[KnowledgeEntry],
        ordered_titles: list[str],
    ) -> list[KnowledgeEntry]:
        """按后台主推配置顺序返回商品，缺失商品保持在末尾。"""
        order_map = {title: index for index, title in enumerate(ordered_titles)}
        return sorted(
            entries, key=lambda entry: order_map.get(entry.title, len(order_map))
        )
