# YunxiBakeBot 项目开发日志 (Logbook)

> 本文档是项目演进的唯一真实编年史。AI（Claude Code）在完成任何功能开发、Bug 修复、架构重构并准备提交前，必须在顶部（或追加到历史最新处）记录本轮变更。

---

## [版本/日期] - 2026-05-19
- **操作人**: AI (Cascade)
- **关联任务/功能**: 甲方测试反馈修复 + 主推款管理页 + 商品上下架管理页
- **核心变更文件说明**:
  - `knowledge/芸熙烘焙通用服务与售后指引.md`: 修复餐具价格 2元→5元；保质期更新为三天保质期，新鲜水果当天最佳。
  - `knowledge/芸熙烘焙产品服务全指南.md`: 细化配送规则；补全门店地址；蛋糕写字4种方式+餐具5元/套；新增营业时间截单规则；新增近期主推款8款。
  - `knowledge/芸熙AI客服指引_Prompt.md`: 更新配送方式说明；新增营业时间规则节。
  - `app/service/chat.py`: 移除运费关键词硬编码拦截，所有配送问题交由 LLM 依据知识库作答。
  - `app/api/admin.py`: 移除测试页运费关键词拦截和 intent==2 硬编码回复。
  - `app/service/llm/prompt.py`: 删除刚性运费话术指令；新增配送/营业时间/主推款推荐规则。
  - `app/models/config.py`: 新建店铺配置模型（ShopConfig/FEATURED_PRODUCTS_KEY）。
  - `app/repository/config_repo.py`: 新建键值配置仓库（get/set/get_list/set_list）。
  - `app/repository/knowledge_repo.py`: 新增 get_all_products、count_products、get_by_id、update_active。
  - `app/service/knowledge_retriever.py`: 接收 ConfigRepo，每次检索结果首位注入主推款合成条目。
  - `app/api/admin_config.py`: 新建路由——主推款管理 + 商品上下架管理 API 及页面。
  - `app/templates/admin/featured_products.html`: 主推款管理页（标签卡片增删保存）。
  - `app/templates/admin/products.html`: 商品上下架管理页（分页列表 + Toggle 开关）。
  - `app/templates/admin/base.html`: 导航栏新增主推款和商品管理两项。
  - `app/database.py`: 新增 shop_config 键值表。
  - `app/main.py`: 注入 ConfigRepo，传给 KnowledgeRetriever，注册 admin_config 路由。
- **数据库状态变更 (Schema Update)**:
  - 新增 `shop_config(key TEXT PK, value TEXT, updated_at TEXT)` 表。
- **测试覆盖与验证结果**:
  - 代码红线自查（Optional/Union/TODO）: ✅ 零输出
- **潜伏风险/遗留未决事项说明 (Risk & Debt)**:
  - 有赞对接后需实现 Webhook 自动调用 update_active 同步商品状态（预留接口已就绪）。

## [版本/日期] - 2026-05-18
- **操作人**: AI (Claude Code)
- **关联任务/功能**: 多任务综合（意图拆分/测试页改造/校验脚本/备份/日志规范）
- **核心变更文件说明**:
  - `app/service/llm/intent.py`: 意图分类从 4 类扩展为 5 类（1-商品, 2-运费, 3-配送时间, 4-售后, 5-闲聊），运费与配送时间分离。
  - `app/service/chat.py`: 新增运费关键词前置匹配（不走 LLM 直接返回固定话术）；意图 4 替换原意图 3 的转人工逻辑；意图 5 替换原意图 4 的闲聊不走知识检索逻辑；全链路 Markdown 星号清理。
  - `app/api/admin.py`: 移除硬编码的旧 intent==3 转人工分支，替换为 intent==4；运费关键词前置匹配优先于意图识别。
  - `app/templates/admin/chat_test.html`: 移除"新对话"按钮；快捷按钮与输入框共用同一会话（`admin_tester`）实现持续对话；更新意图标签映射为 5 类；Bearer token 同步更新。
  - `scripts/test_scenarios.py`: 意图标签映射更新为 5 类。
  - `scripts/validate_products.py`: 新建商品数据校验脚本，逐条验证 765 条商品的价格合法性、编码异常、截断、括号闭合等。
  - `tests/scripts/test_validate_products.py`: 新建 21 条单元测试（含内存 SQLite Mock 数据），覆盖正常/脏数据/空价格/混合数据等边界 Case，漏报率为 0。
  - `scripts/backup_db.sh`: 新建 SQLite 热备份脚本，使用 `.backup` 命令，含完整性验证和 72 小时旧备份清理。
  - `CLAUDE.md`: 新增常用开发命令清单和 AI 预提交红线审查守则。
  - `LOGBOOK.md`: 新建项目开发日志。
- **数据库状态变更 (Schema Update)**:
  - 无
- **测试覆盖与验证结果**:
  - `python scripts/test_scenarios.py` ✅ 正确识别运费/配送/商品/售后/闲聊 5 类意图
  - `python scripts/test_intents.py` ✅ 7 个场景全部通过
  - `python tests/scripts/test_validate_products.py` ✅ 21/21 Passed
  - `python scripts/validate_products.py` ✅ 765 条商品校验完成（0 ERROR, 49 WARNING）
- **潜伏风险/遗留未决事项说明 (Risk & Debt)**:
  - validate_products.py 输出的 49 条 WARNING 中大部分为"价格超出基准区间"——提拉米苏蛋糕（198-388元）和生日蛋糕（408-608元）的大尺寸版本超出当前保守区间，需人工确认后调整 `CORE_PRICE_RANGES`。
  - 部分商品标题存在中英文括号混用（如"（xxx)"或"(xxx）"），数据源需统一规范化处理。
  - 企微接入待 SCF 函数 URL 回调验证通过后上线。
  - 企微 API 客户端已就绪（access_token 缓存、消息发送）。
  - SCF 转发代理（scripts/scf_proxy.py）已编写，需部署后测试。
  - 转人工服务的消息推送仅支持管理后台轮询。

---

## [版本/日期] - 2026-05-18
- **操作人**: AI (Claude Code)
- **关联任务/功能**: 后台管理大改版 + 知识库扩容 + 企微回调预备
- **核心变更文件说明**:
  - `app/templates/admin/chat_test.html`: 完全重写为微信风格全屏聊天UI，消息气泡/输入栏/抽屉菜单/保存对话/弹窗等，手机端优先。
  - `app/templates/admin/base.html`: 新增移动端顶栏（sticky topbar + hamburger），侧栏改为抽屉式滑动。
  - `app/templates/admin/transfers.html`: 重构布局，新增对话查看面板（右侧抽屉）、修复接单/查看对话无Token问题。
  - `app/static/admin/style.css`: 全面重写响应式CSS，移动/平板/PC三端适配。
  - `app/api/admin.py`: 新增 chat-test 历史消息API、保存命名API、丢弃对话API、查看会话消息API；注入 message_repo 依赖。
  - `app/repository/session_repo.py`: 新增 `update_extra()`、`get_named()` 方法，支持对话命名/列表/丢弃状态过滤。
  - `app/main.py`: 注入 message_repo 参数。
  - `app/service/llm/intent.py`: 意图分类调整为5类（商品/运费/配送/售后/闲聊），下单关键词归入商品类。
  - `app/service/llm/prompt.py`: 新增尺寸人数强制从知识库的规则。
  - `scripts/seed_knowledge.py`: 新增 `parse_scripts()` 解析话术库；新增全指南文件导入。
  - `knowledge/芸熙烘焙产品服务全指南.md`: 新增，整合资料.md为结构化FAQ+话术库。
  - `scripts/scf_proxy.py`: 修复VPS地址为公网IP。
- **数据库状态变更 (Schema Update)**:
  - 无
- **测试覆盖与验证结果**:
  - `python scripts/test_scenarios.py` ✅ 5类意图识别正确
  - `python scripts/validate_products.py` ✅ 765条校验通过
  - `python scripts/seed_knowledge.py` ✅ 806条知识导入完成
  - 对话保存/命名/丢弃/加载历史 ✅ 全链路测试通过
- **潜伏风险/遗留未决事项说明 (Risk & Debt)**:
  - 企微回调域名主体校验未通过，需等公司域名备案后才能启用。
  - 管理员前台专注对话测试和数据统计定位，转人工/接单功能已置灰待上线。
  - 对话测试页 + 按钮可能存在移动端兼容问题（需在真机测试）。
  - AI偶有编造尺寸食用人数的问题，已通过 prompt 规则缓解，需持续标注跟进。

---

## [版本/日期] - 2026-05-18
- **操作人**: AI (Claude Code)
- **关联任务/功能**: Bug修复 + 登录简化
- **核心变更文件说明**:
  - `app/templates/admin/login.html`: 去除密码输入，自动登录跳转到对话测试页。
  - `app/templates/admin/chat_test.html`: 新增 `loadHistory()` 页面加载时恢复历史消息；丢弃对话时关闭旧会话不再残留；删除对话同时清空当前画布。
  - `app/api/admin.py`: 历史消息接口返回 `session_id` 供前端绑定。
- **数据库状态变更 (Schema Update)**:
  - 无
- **测试覆盖与验证结果**:
  - 对话保存/丢弃/刷新恢复全链路 ✅
- **潜伏风险/遗留未决事项说明 (Risk & Debt)**:
  - 企微域名备案问题仍在等待。
