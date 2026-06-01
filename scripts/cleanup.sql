DELETE FROM knowledge_base WHERE id IN (9575, 9576, 9568, 9570, 9574, 9569, 9572, 9573);

UPDATE knowledge_base 
SET content = replace(content, '超时 30 分钟以上', '超时 1 小时以上'), 
    updated_at = datetime('now') 
WHERE id = 9565;

UPDATE knowledge_base 
SET content = replace(content, '绝不使用植物奶油（人造奶油）', '由安佳北京总部直供配送，绝不使用植物奶油（人造奶油）'), 
    updated_at = datetime('now') 
WHERE id = 9562;

UPDATE knowledge_base 
SET content = replace(content, '我们的生日蛋糕通常提供多种尺寸选择，包括 6寸、8寸、10寸、12寸 等，不同款式可选尺寸有所不同，详见具体款式介绍。', '我们的生日蛋糕通常提供多种尺寸选择：
- **6寸**（直径15cm）：建议 5 人以内食用。
- **8寸**（直径20cm）：建议 10 人以内食用。
- **10寸**（直径25cm）：建议 15 人以内食用。
- **12寸**（直径30cm）：建议 20 人以内食用。
不同款式可选尺寸有所不同，详见具体款式介绍。'), 
    updated_at = datetime('now') 
WHERE id = 9546;

UPDATE knowledge_base 
SET content = replace(content, '- **北京同城配送**：默认使用闪送一对一配送，运费根据距离核算，由顾客自理。', '- **北京同城配送**：默认使用闪送一对一配送，运费根据距离核算，由顾客自理。我们的蛋糕定价为自提基准价格，未将高昂的冷链快递费平摊加价，对不同距离客户和自提客户更加公平。'), 
    updated_at = datetime('now') 
WHERE id = 9561;
