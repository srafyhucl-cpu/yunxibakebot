"""ChatService 的多模态消息构造边界。"""

import base64

from app.logger import setup_logger

logger = setup_logger()

DEFAULT_IMAGE_MIME_TYPE = "image/jpeg"
PNG_SIGNATURE = b"\x89PNG"
JPEG_SIGNATURE = b"\xff\xd8"
WEBP_SIGNATURE = b"RIFF"
IMAGE_HEADER_SAMPLE_CHARS = 32
IMAGE_HEADER_BYTES = 4
IMAGE_EMPTY_TEXT = "[用户发送了一张图片]"


def normalize_image_data_uri(image_base64: str) -> str:
    if image_base64.startswith("data:"):
        return image_base64

    header_bytes = base64.b64decode(image_base64[:IMAGE_HEADER_SAMPLE_CHARS])[
        :IMAGE_HEADER_BYTES
    ]
    mime_type = DEFAULT_IMAGE_MIME_TYPE
    if header_bytes[:IMAGE_HEADER_BYTES] == PNG_SIGNATURE:
        mime_type = "image/png"
    elif header_bytes[0:2] == JPEG_SIGNATURE:
        mime_type = "image/jpeg"
    elif header_bytes[0:IMAGE_HEADER_BYTES] == WEBP_SIGNATURE:
        mime_type = "image/webp"
    return f"data:{mime_type};base64,{image_base64}"


def apply_multimodal_image_message(
    messages: list[dict],
    image_base64: str,
    session_id: str,
) -> None:
    image_data_uri = normalize_image_data_uri(image_base64)
    for index in range(len(messages) - 1, -1, -1):
        if messages[index].get("role") != "user":
            continue

        original_text = messages[index].get("content", "") or ""
        messages[index] = {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_data_uri},
                },
                {
                    "type": "text",
                    "text": original_text or IMAGE_EMPTY_TEXT,
                },
            ],
        }
        logger.info(
            "会话 %s 已构建多模态消息（图片 %d 字符 base64）",
            session_id,
            len(image_base64),
        )
        return
