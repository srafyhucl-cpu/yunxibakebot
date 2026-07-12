"""微信客服商品卡片发送。"""

from app.logger import setup_logger

logger = setup_logger()


async def send_kf_card(client, external_userid: str, card: dict) -> None:
    """发送商品 link 卡片，失败时降级为文本。"""
    title = card.get("title", "商品推荐")
    price = card.get("price", "")
    img_url = card.get("src", "")
    link_url = card.get("url", "")
    description = f"¥{price}" if price else title
    thumb_media_id = ""

    if img_url:
        try:
            img_resp = await client._client.get(img_url, timeout=10)
            if img_resp.status_code == 200:
                img_data = await img_resp.aread()
                logger.info(
                    "已下载商品图片 size=%dB url=%s", len(img_data), img_url[:80]
                )
                thumb_media_id = await client.upload_kf_temp_media(
                    file_data=img_data,
                    file_type="image",
                    file_name=f"{title}.jpg",
                )
            else:
                logger.warning(
                    "下载商品图片失败 status=%d url=%s",
                    img_resp.status_code,
                    img_url[:80],
                )
        except Exception as exc:
            logger.warning("下载/上传商品图片异常 url=%s err=%s", img_url[:80], exc)

    result = await client.send_kf_link(
        external_userid=external_userid,
        title=title,
        url=link_url or "",
        desc=description,
        thumb_media_id=thumb_media_id or "",
    )
    if result.get("errcode") == 0:
        logger.info("客服商品卡片已发送 user=%s title=%s", external_userid, title)
        return

    logger.warning(
        "客服link卡片发送失败，降级为文本消息 user=%s err=%s",
        external_userid,
        result.get("errmsg"),
    )
    text_parts = [f"📦 {title}"]
    if price:
        text_parts.append(f"💰 ¥{price}")
    if link_url:
        text_parts.append(f"🔗 {link_url}")
    if img_url:
        text_parts.append(f"🖼️ {img_url}")

    text_result = await client.send_kf_text(external_userid, "\n".join(text_parts))
    if text_result.get("errcode") != 0:
        logger.error(
            "客服商品卡片文本降级也失败 user=%s err=%s",
            external_userid,
            text_result.get("errmsg"),
        )
