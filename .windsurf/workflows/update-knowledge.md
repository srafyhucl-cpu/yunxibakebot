---
description: 知识库更新工作流，用于将烘焙业务文档（Word/PDF/Excel/图片）导入芸熙知识库，或对已有知识条目进行增删改
---

# 知识库更新工作流

## 触发场景

- 新增 / 修改产品信息、价格、规格
- 更新服务规则、售后政策、配送规则
- 导入外部业务文档（Word/PDF/Excel）到 `knowledge/` 目录

## 步骤

### 1. 如有外部文档，先转换为 Markdown

**调用 `markitdown` skill**，将文档转换为 Markdown：

- Word / PDF / Excel / PowerPoint → 直接转换
- 图片（含文字） → OCR 提取
- 转换后保存到 `knowledge/` 目录下对应文件

### 2. 确认知识口径无冲突

对照以下现有文件，确认新内容是否与现有口径有冲突：

- `knowledge/芸熙烘焙产品服务全指南.md`
- `knowledge/芸熙烘焙常见问题FAQ.md`
- `knowledge/芸熙烘焙通用服务与售后指引.md`

**任何口径冲突必须先确认，不得自动覆盖。**

### 3. 更新 Markdown 知识文件

按类别更新对应文件，保持现有结构。

### 4. 重新生成向量索引

```powershell
# 删除旧的嵌入缓存，触发重建
Remove-Item "data/embeddings.pkl" -ErrorAction SilentlyContinue

# 重新导入知识库（本地）
python scripts/seed_knowledge.py
```

### 5. 验证导入结果

```powershell
# 检查知识条目数量
python scripts/validate_products.py
```

### 6. 更新 LOGBOOK.md

记录本次知识库变更内容和条目数量变化。
