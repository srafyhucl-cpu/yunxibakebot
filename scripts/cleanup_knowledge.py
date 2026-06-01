import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import init_db
from app.repository.knowledge_admin_repo import KnowledgeAdminRepo
from app.models.knowledge_admin import KnowledgeAdminDraft
from app.logger import setup_logger
from app.models.content_change_history import SyncSource

logger = setup_logger()

async def cleanup():
    conn = await init_db("data/bot.db")
    try:
        repo = KnowledgeAdminRepo(conn)
        
        # 1. 批量删除
        to_delete = [9575, 9576, 9568, 9570, 9574]
        for aid in to_delete:
            try:
                await repo.delete_entry(aid, operator="system_cleanup")
                logger.info(f"Deleted ID {aid}")
            except Exception as e:
                logger.warning(f"Failed to delete {aid}: {e}")

        # 2. 更新 9565 (超时标准统一为1小时)
        try:
            entry_9565 = await repo.get_entry_by_id(9565)
            if entry_9565:
                content = entry_9565.content.replace("超时 30 分钟以上", "超时 1 小时以上")
                draft = KnowledgeAdminDraft(
                    title=entry_9565.title,
                    content=content,
                    content_type=entry_9565.content_type,
                    keywords=entry_9565.keywords,
                    priority=entry_9565.priority,
                    is_active=entry_9565.is_active
                )
                await repo.update_entry(9565, draft, operator="system_cleanup")
                logger.info("Updated ID 9565 (超时标准)")
        except Exception as e:
            logger.warning(f"Failed to update 9565: {e}")

        # 3. 更新 9562 (奶油总部直供)
        try:
            entry_9562 = await repo.get_entry_by_id(9562)
            if entry_9562:
                content = entry_9562.content.replace(
                    "绝不使用植物奶油（人造奶油）", 
                    "由安佳北京总部直供配送，绝不使用植物奶油（人造奶油）"
                )
                draft = KnowledgeAdminDraft(
                    title=entry_9562.title,
                    content=content,
                    content_type=entry_9562.content_type,
                    keywords=entry_9562.keywords,
                    priority=entry_9562.priority,
                    is_active=entry_9562.is_active
                )
                await repo.update_entry(9562, draft, operator="system_cleanup")
                logger.info("Updated ID 9562 (奶油总部直供)")
        except Exception as e:
            logger.warning(f"Failed to update 9562: {e}")

        # 4. 更新 9546 (补充详细尺寸)
        try:
            entry_9546 = await repo.get_entry_by_id(9546)
            if entry_9546:
                content = entry_9546.content.replace(
                    "我们的生日蛋糕通常提供多种尺寸选择，包括 6寸、8寸、10寸、12寸 等，不同款式可选尺寸有所不同，详见具体款式介绍。",
                    "我们的生日蛋糕通常提供多种尺寸选择：\n- **6寸**（直径15cm）：建议 5 人以内食用。\n- **8寸**（直径20cm）：建议 10 人以内食用。\n- **10寸**（直径25cm）：建议 15 人以内食用。\n- **12寸**（直径30cm）：建议 20 人以内食用。\n不同款式可选尺寸有所不同，详见具体款式介绍。"
                )
                draft = KnowledgeAdminDraft(
                    title=entry_9546.title,
                    content=content,
                    content_type=entry_9546.content_type,
                    keywords=entry_9546.keywords,
                    priority=entry_9546.priority,
                    is_active=entry_9546.is_active
                )
                await repo.update_entry(9546, draft, operator="system_cleanup")
                logger.info("Updated ID 9546 (详细尺寸说明)")
        except Exception as e:
            logger.warning(f"Failed to update 9546: {e}")
            
        # 5. 更新 9561 (配送与定价)
        try:
            entry_9561 = await repo.get_entry_by_id(9561)
            if entry_9561:
                content = entry_9561.content.replace(
                    "- **北京同城配送**：默认使用闪送一对一配送，运费根据距离核算，由顾客自理。",
                    "- **北京同城配送**：默认使用闪送一对一配送，运费根据距离核算，由顾客自理。我们的蛋糕定价为自提基准价格，未将高昂的冷链快递费平摊加价，对不同距离客户和自提客户更加公平。"
                )
                draft = KnowledgeAdminDraft(
                    title=entry_9561.title,
                    content=content,
                    content_type=entry_9561.content_type,
                    keywords=entry_9561.keywords,
                    priority=entry_9561.priority,
                    is_active=entry_9561.is_active
                )
                await repo.update_entry(9561, draft, operator="system_cleanup")
                logger.info("Updated ID 9561 (配送定价)")
        except Exception as e:
            logger.warning(f"Failed to update 9561: {e}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(cleanup())
