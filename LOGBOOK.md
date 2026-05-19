# YunxiBakeBot 项目开发日志 (Logbook)

> 本文档是项目演进的唯一真实编年史。AI（Claude Code）在完成任何功能开发、Bug 修复、架构重构并准备提交前，必须在顶部（或追加到历史最新处）记录本轮变更。

---

## [版本/日期] - 2026-05-19
- **操作人**: AI (Cascade)
- **关联任务/功能**: 知识库统一管理与规则来源归口
- **核心变更文件说明**:
  - `scripts/seed_knowledge.py`: 从“绑定旧混合文档”切换为“按中粒度目录结构导入”，当前只读取 `knowledge/规则/`、`knowledge/FAQ/`、`knowledge/话术/` 下启用的主文档，避免继续依赖旧混合知识源。
  - `knowledge/README.md`: 新增知识库目录首页，明确商品、规则、FAQ、话术、参考五类目录的维护入口。
  - `knowledge/规则/README.md` / `knowledge/FAQ/README.md` / `knowledge/话术/README.md`: 为各子目录补充局部导航说明，帮助维护者进入子目录后快速判断每个文件的职责边界与入库方式。
  - `knowledge/规则/订购与履约规则.md` / `商品通用规则.md` / `售后规则.md` / `企业服务规则.md`: 将通用业务规则收敛为 4 份中粒度主文档，每份只负责一类规则面。
  - `knowledge/FAQ/基础服务FAQ.md` / `商品选购FAQ.md` / `场景与会员FAQ.md`: 将 FAQ 收敛为 3 份中粒度主文档，分别承接基础问答、选购问答与场景会员问答。
  - `knowledge/话术/下单引导话术.md` / `售后安抚话术.md`: 将客服话术独立出 FAQ 与规则目录，减少混合维护。
  - `knowledge/规则/`、`knowledge/FAQ/`: 删除上一轮过细拆分遗留的草稿文件，仅保留最终启用的中粒度主文档，避免维护入口再次分叉。
  - `knowledge/芸熙烘焙通用服务与售后指引.md` / `芸熙烘焙常见问题FAQ.md` / `芸熙烘焙产品服务全指南.md`: 改为历史归档入口，不再参与运行时入库，防止维护者误改旧文件。
  - `knowledge/芸熙烘焙商品库知识库.md`: 删除烟花蜡烛条目并清理蛋糕标题中的烟花蜡烛断货描述，避免商品资料与统一配件规则冲突。
  - `knowledge/芸熙烘焙商品库知识库.md` / `knowledge/芸熙烘焙常见问题FAQ.md` / `knowledge/芸熙烘焙通用服务与售后指引.md` / `knowledge/芸熙烘焙产品服务全指南.md` / `knowledge/芸熙AI客服指引_Prompt.md`: 补充文档分类、是否直接入库、维护边界与生效说明，降低后续维护改错文件的风险。
  - `knowledge/知识源说明.md`: 新增知识源说明文档，统一说明知识文档分类、单一来源原则、维护入口、入库关系与日常维护流程。
  - `app/service/llm/prompt.py`: 去掉营业时间硬编码，改为要求严格依据店铺知识回答，避免 Prompt 与知识源双维护。
- **数据库状态变更 (Schema Update)**:
  - 无新增表结构；已执行 `python scripts/seed_knowledge.py` 全量重建知识库，当前共 796 条知识。
  - 已重建 `data/embeddings.pkl`，向量索引同步为 796 条知识，避免沿用旧结构与旧标题文本。
- **测试覆盖与验证结果**:
  - `python scripts/seed_knowledge.py` ✅ 成功导入 796 条知识。
  - `python scripts/check_project.py` ✅ 质量门禁通过，红线检查与 `tests/scripts/test_validate_products.py` 全部通过。
  - `python scripts/validate_products.py` ✅ 0 Error / 53 Warning；均为商品库历史数据告警，本次知识结构重构未新增商品数据异常。
  - 新结构抽查：`订购与履约规则`、`商品通用规则`、`企业服务规则`、`配送损坏处理`、`漏发配件处理`、`配送超时处理`、`话术1 主动询问需求`、`话术10 漏发配件话术`、`适合母亲节送礼的蛋糕有哪些推荐？`、`积分怎么用？` 已成功入库。
  - `知识源说明.md` 入库校验：`knowledge_base` 中相关条目计数为 `0`，说明文档未被误导入。
  - 深度回归验证：知识库总量 `796`、Embedding 文档数 `796`、重复执行 `python scripts/seed_knowledge.py` 后数据库快照哈希一致，确认导入幂等。
  - 线上抽样回归：`积分怎么用`、`蛋糕可以放几天`、`怎么配送`、`母亲节有什么推荐` 返回内容与本轮知识重构口径一致；`蛋糕送坏了怎么办` 正常转人工。
- **潜伏风险/遗留未决事项说明 (Risk & Debt)**:
  - 深测发现混合检索对“可以开发票吗”这类自然问句仍可能夹带少量无关 FAQ 或商品结果；当前线上链路会先做 `rewrite_query`，不影响本次知识结构上线，但后续仍应在 `app/service/knowledge_retriever.py` 与 `app/repository/knowledge_repo.py` 继续优化排序与过滤。
  - 线上抽样发现 `可以开发票吗` 仍会被误判为售后并直接转人工，说明问题不只在检索排序，还涉及意图识别或发票规则兜底策略，需后续专项修复。
  - 服务器同步时若直接用绝对路径执行 `scripts/seed_knowledge.py` 而未先 `cd /opt/yunxibakebot`，相对路径 `data/bot.db` 可能误写到错误工作目录；后续线上重灌知识库必须先切到项目根目录再执行脚本。
- **关联任务/功能**: 修复管理后台 chat-test 500 与 FAQ 精确命中
- **核心变更文件说明**:
  - `app/service/admin.py`: 补齐管理后台 API 依赖的会话查询、消息查询、状态更新与扩展信息更新代理方法，避免 API 层直接穿透 Repository。
  - `app/api/admin.py`: 修复 chat-test 复用非默认测试用户时仍处于人工服务状态导致 AI 跳过并返回空回复的问题。
  - `app/service/knowledge_retriever.py`: 调整混合检索逻辑，始终合并关键词结果与向量结果，确保新增精确 FAQ 不被向量结果挤掉。
  - `app/service/chat.py`: 抽取知识装载 helper；当意图误判为 `CASUAL_CHAT` 时，先做关键词精确 FAQ 检索，避免“积分怎么用”这类店铺规则问题丢失知识上下文。
  - `app/service/llm/intent.py`: 强化意图识别规则，明确“积分/优惠券/会员/店铺规则”属于业务咨询，并要求当前输入优先，避免被历史售后上下文带偏为转人工。
  - `app/api/admin.py`: 移除 chat-test 路由层的售后提前短路，统一由 `ChatService` 决定最终分支，避免页面显示意图与实际执行结果不一致。
  - `app/templates/admin/chat_test.html`: 停止按 `user_id` 自动恢复临时测试会话，默认生成新的临时用户，仅恢复已保存会话，消除历史上下文污染导致“问什么都跑偏/显示无回复”的问题。
  - `app/templates/admin/chat_test.html`: 恢复未保存会话的 `sessionId` 回显能力，并修正“新增对话”按钮的弹窗判定，避免首次进入看不到刚才对话、二次点击才弹保存框从而丢失会话。
  - `app/templates/admin/chat_test.html`: 优化聊天页抽屉导航，新增“当前会话”状态卡、保存/新建快捷操作、卡片化页面导航、已保存对话高亮与时间信息展示，以及更清晰的快捷测试入口。
  - `app/service/admin.py`: 补齐 `get_all_active` 与 `get_recent` 兼容方法，修复移动端从聊天页抽屉点击“概览”或后续进入转人工页时的 `50000 服务器内部错误`。
  - `app/templates/admin/chat_test.html`: 修复右上角“新对话”按钮在无当前会话时看似无反应的问题，点击后会明确进入新对话、聚焦输入框并给出提示反馈。
- **测试覆盖与验证结果**:
  - `python scripts/check_project.py` ✅ 质量门禁通过。
  - `pytest tests/service/test_admin.py` ✅ 2 passed。
- **潜伏风险/遗留未决事项说明 (Risk & Debt)**:
  - `app/api/admin.py` 仍为存量警戒文件，本次仅修复错误调用，不新增路由职责。
  - `app/service/chat.py` 虽超警戒线，但本次仅抽取 `_load_knowledge_entries` 以减少 `_ai_conversation_loop` 的职责密度；知识检索与对话编排仍属紧密内聚，暂不拆文件。

## [版本/日期] - 2026-05-19
- **操作人**: AI (Cascade)
- **关联任务/功能**: 高阶 DevOps 配置接入与历史红线违约清查
- **核心变更文件说明**:
  - `app/service/admin.py`: 新增。剥离 `admin_config.py` 和 `admin.py` 的 API 层中对 Repository 层的直接调用，补全业务薄层，符合 `api -> service -> repo` 分层约束。
  - `app/repository/knowledge_repo.py`: 修复。重构 IN 参数绑定逻辑，彻底消除潜在 SQL f-string 拼接报警风险。
  - `.pre-commit-config.yaml`: 新增。配置 `check_project.py` 为 Git Hook，本地防呆强制拦截红线。
  - `.github/workflows/ci.yml`: 新增。云端 CI 流水线（支持自动装依赖、跑门禁、数据 Mock 生成、以及只读冒烟测试闭环）。
  - `tests/service/test_admin.py`: 新增。应用 `AsyncMock` 技术，提供纯净不依赖底层数据库的 `AdminService` 单测范例。
  - `scripts/check_project.py`: 清除所有的 `LEGACY` 白名单，恢复 100% 刚性阻断。
- **测试覆盖与验证结果**:
  - `pytest tests/service/test_admin.py` ✅ 2 passed（毫秒级 Service 隔离测试完成）。
  - `python scripts/check_project.py` ✅ 所有历史红线警告已通过清偿与重构清零（0 存量违规）。
- **潜伏风险/遗留未决事项说明 (Risk & Debt)**:
  - `app/service/chat.py` 仍存在职责过载（行数超警戒线）但已做暂时隔离；待后续重构聊天链路时拆分。

## [版本/日期] - 2026-05-19
- **操作人**: AI (Cascade)
- **关联任务/功能**: Harness Engineering 工程化支持升级
- **核心变更文件说明**:
  - `scripts/check_project.py`: 新增。统一质量门禁脚本，固化了 `CLAUDE.md` 中的红线规则（单引号、Optional、SELECT *、架构分层防穿透等），并支持 Windows UTF-8 emoji 输出测试。
  - `scripts/smoke_test.py`: 新增。只读环境探针脚本，用于一键检查依赖环境（包括 .env 存在性、数据库表结构完整性、知识库加载状态、Embedding 文件存在性及服务 /health 接口存活状态）。
  - `pytest.ini`: 新增。配置 `pytest` 自动发现入口。
  - `requirements-dev.txt`: 新增。分离开发依赖（包含 `pytest`、`ruff`、`pre-commit`、`detect-secrets` 等），解耦生产依赖与工具链。
- **数据库状态变更 (Schema Update)**:
  - 触发了 `shop_config` 表的初始化构建（此前仅存在于 schema 声明中未落地开发库）。
- **测试覆盖与验证结果**:
  - `python scripts/check_project.py` ✅ 红线约束与 `test_validate_products.py`（21 passed）双通过。暂未彻底阻断的存量违约已作 LEGACY 标识登记。
  - `python scripts/smoke_test.py` ✅ 环境探针（7 项指标）全数 PASS。
- **潜伏风险/遗留未决事项说明 (Risk & Debt)**:
  - `app/api/admin.py` 和 `app/service/chat.py` 行数超限问题已确认，考虑到本轮未触及相关业务逻辑未强行重构；这些文件中的 `LEGACY`（如直接 import repository）继续保持登记预警，择期在重构独立任务中一并消除。

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
