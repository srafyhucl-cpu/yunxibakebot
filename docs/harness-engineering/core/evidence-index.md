# Evidence Index

本文件是 Harness 证据包索引。它不保存敏感报告内容，只记录证据文件的位置、用途、生成命令和验证结论，方便上线前后审计、复盘和交接。

______________________________________________________________________

## 证据目录

| 目录 | 用途 |
|---|---|
| `reports/harness/` | Harness 快照、交接、汇总索引 |
| `reports/preflight-*.json` | 生产同步前后预检报告 |
| `reports/smoke-*.json` | 冒烟测试报告 |
| `reports/migration-*.json` | 数据库迁移 dry-run / apply 报告 |
| `reports/baseline-seed-*.json` | 基础知识种子 dry-run / apply 报告 |
| `reports/rebuild-embeddings-*.json` | 向量重建 dry-run / apply 报告 |

______________________________________________________________________

## E-20260617-046：生产后台浏览器只读导航 smoke

- trace_id: 20260617-production-admin-browser-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command/release
- file: `D:\Project\YunxiBakeBot\reports\ui\production-admin-browser-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\production-admin-browser-smoke.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260617-131610.json`
- command: `npm run smoke:production-navigation` in `YunxiBakeBot\web\admin`; `npm run check:production-admin-browser`; `npm run release:readiness`
- result: pass
- related_logbook: 2026-06-17 - test(production): 生产后台浏览器只读导航 smoke
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留生产后台浏览器截图和 JSON 报告；token 仅通过环境变量临时注入，不写入报告
- summary: 生产后台登录后只读访问概览、装修、订单、地址、商品、转人工、店铺配置 7 个页面均渲染成功；小程序 release readiness 升级为 21/21 通过。

## E-20260620-002：有赞客户迁移交接与回滚 runbook

- trace_id: 20260620-customer-import-handoff
- generated_at: 2026-06-20
- evidence_type: handoff/runbook
- file: `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-import-handoff-and-rollback-runbook.md`; `D:\Project\YunxiBakeBot\docs\README.md`
- command: `Test-Path docs/architecture/youzan-customer-import-handoff-and-rollback-runbook.md`; `Select-String -Path docs/README.md -Pattern "youzan-customer-import-handoff-and-rollback-runbook"`
- result: pass
- related_logbook: 2026-06-20 - docs(customer): 补齐有赞客户迁移交接回滚 runbook
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留交接与回滚 runbook 的摘要索引；不包含具体客户数据、数据库内容或报告正文。
- summary: 有赞客户正式迁移现在同时具备“怎么迁、怎么核对、出事后怎么停、怎么交接、怎么恢复”的完整文档链路；后续补跑、事故处理和换手不必再靠聊天记录临场拼接。

## E-20260620-003：客户迁移闭环入口收束

- trace_id: 20260620-customer-master-next-steps; 20260620-root-readme-customer-links; 20260620-platform-miniapp-contract-customer-links; 20260620-miniapp-handoff-customer-links; 20260620-customer-import-boundary-links; 20260620-customer-master-schema-next-steps; 20260620-customer-audit-next-steps; 20260620-customer-loop-four-sections
- generated_at: 2026-06-20
- evidence_type: handoff/runbook/doc
- file: `D:\Project\YunxiBakeBot\README.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\customer-master-v1-schema-draft.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-migration-audit-checklist.md`; `D:\Project\YunxiBakeBot\docs\architecture\platform-miniapp-api-contract-v1.md`; `D:\Project\YunxiBakeBot\docs\architecture\miniapp-ai-handoff-plan.md`; `D:\Project\YunxiBakeBot\docs\architecture\miniapp-phase1-execution-checklist.md`; `D:\Project\YunxiBakeBot\docs\architecture\project-boundaries.md`; `D:\Project\YunxiBakeBot\docs\architecture\two-repo-rollout-plan.md`
- command: `Select-String -Path README.md,docs/architecture/customer-master-v1.md,docs/architecture/customer-master-v1-schema-draft.md,docs/architecture/youzan-customer-migration-audit-checklist.md,docs/architecture/platform-miniapp-api-contract-v1.md,docs/architecture/miniapp-ai-handoff-plan.md,docs/architecture/miniapp-phase1-execution-checklist.md,docs/architecture/project-boundaries.md,docs/architecture/two-repo-rollout-plan.md -Pattern "youzan-customer-migration-audit-checklist|youzan-customer-formal-import-runbook|youzan-customer-import-handoff-and-rollback-runbook|verify_youzan_customer_import"`
- result: pass
- related_logbook: 2026-06-20 - docs(architecture): 统一客户迁移闭环为四段口径; 2026-06-20 - docs(architecture): 更新 customer master v1 的后续入口; 2026-06-20 - docs(architecture): 更新 customer master schema 草案的实施建议; 2026-06-20 - docs(architecture): 更新客户迁移审计清单的后续入口; 2026-06-20 - docs(readme): 在根入口补齐客户迁移闭环; 2026-06-20 - docs(architecture): 补齐双仓 API 契约中的客户迁移权威入口; 2026-06-20 - docs(architecture): 收束 MiniApp 接力文档的客户迁移入口; 2026-06-20 - docs(architecture): 收束客户迁移入口到边界文档
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留客户迁移入口收束后的统一索引；仅记录文档入口与验证命令，不包含客户数据与执行报告正文。
- summary: 客户迁移闭环入口已经从 README、主档设计、schema 草案、审计清单、双仓 API 契约、MiniApp 历史接力文档和上层边界文档全部打通，并统一为审计、正式迁移、迁移后核对、交接/回滚四段口径，后续无论从产品、架构、接力还是执行入口进入，都能直接跳到同一套权威材料。

## E-20260617-045：生产后台 MVP 前端 dist 部署

- trace_id: 20260617-production-admin-frontend-check
- generated_at: 2026-06-17
- evidence_type: release/command/deploy
- file: `D:\Project\YunxiBakeMiniApp\reports\production-admin-check\production-admin-20260617-045345.json`; `D:\Project\YunxiBakeMiniApp\reports\production-admin-check\latest.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260617-125450.json`
- command: `npm run typecheck` and `npm run build` in `YunxiBakeBot\web\admin`; `npm run check:production-admin`; `npm run release:readiness`
- result: pass
- related_logbook: 2026-06-17 - deploy(production): 部署后台 MVP 前端 dist
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留生产后台前端检查和 readiness 报告；远程保留部署前 dist 备份目录，不包含密钥
- summary: 生产 `/admin/` 已切换到当前后台 MVP dist，包含装修、订单、地址、商品、转人工和店铺配置关键页面 chunk；小程序 release readiness 升级为 19/19 通过。

## E-20260617-044：生产小程序只读 API 切通

- trace_id: 20260617-production-miniapp-api-check
- generated_at: 2026-06-17
- evidence_type: release/command/deploy
- file: `D:\Project\YunxiBakeMiniApp\reports\production-api-check\production-miniapp-api-20260617-043836.json`; `D:\Project\YunxiBakeMiniApp\reports\production-api-check\latest.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260617-123907.json`
- command: `npm run check:production-miniapp-api`; `npm run release:readiness`; remote `systemctl restart/start yunxibakebot`
- result: pass
- related_logbook: 2026-06-17 - deploy(production): 切通小程序只读 API
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留生产只读 API 检查和 readiness 报告；远程保留同步前 app 备份目录，不包含密钥或证书私钥
- summary: 生产后端同步本地 MVP `app/` 代码后，小程序公开只读 API `/api/v1/miniapp/pages/home`、`/api/v1/miniapp/products`、`/api/v1/miniapp/shop-settings` 均返回 `code=0`；小程序 release readiness 升级为 18/18 通过。

## E-20260617-043：release readiness 纳入生产域名门槛

- trace_id: 20260617-release-readiness-gate
- generated_at: 2026-06-17
- evidence_type: release/command
- file: `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260617-112414.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\latest.json`; `D:\Project\YunxiBakeMiniApp\reports\domain-check\domain-check-20260617-032342.json`
- command: `npm run release:readiness` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - test(release): readiness 纳入生产域名门槛
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 release readiness 与生产域名检查报告，不包含密钥或证书私钥
- summary: 小程序发布 readiness 已新增 `production domain HTTPS check`，当前 17/17 checks passed；生产 `yunxifood.cn` 连通性检查成为发布前固定门槛。

## E-20260617-042：yunxifood.cn 根入口与证书切通

- trace_id: 20260617-domain-switch-yunxifood
- generated_at: 2026-06-17
- evidence_type: command/doc
- file: `D:\Project\YunxiBakeMiniApp\reports\domain-check\domain-check-20260617-032041.json`; `D:\Project\YunxiBakeMiniApp\reports\domain-check\latest.json`; `D:\Project\YunxiBakeBot\scripts\yunxifood.cn.nginx.conf`; `D:\Project\YunxiBakeBot\docs\design\4-上线检查清单.md`
- command: `npm run check:production-domain` in `YunxiBakeMiniApp`; remote `nginx -t && systemctl reload nginx`; `curl https://yunxifood.cn/health`; `curl https://yunxifood.cn`
- result: pass
- related_logbook: 2026-06-17 - chore(release): 域名统一切换到 yunxifood.cn
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留生产域名检查 JSON 与 Nginx 模板，不包含密钥或证书私钥
- summary: `yunxifood.cn` 已启用正确证书并在根路径返回后台入口页，`/health` 返回 200，`/` 由 Nginx 精确重定向到 `/admin/`；后端发布文档与本地 Nginx 模板同步更新。

## E-20260617-041：域名统一切换到 yunxifood.cn

- trace_id: 20260617-domain-switch-yunxifood
- generated_at: 2026-06-17
- evidence_type: command/doc
- file: `D:\Project\YunxiBakeBot\docs\design\1-业务方案.md`; `D:\Project\YunxiBakeBot\docs\design\2-工作流设计.md`; `D:\Project\YunxiBakeBot\docs\design\3-技术架构.md`; `D:\Project\YunxiBakeBot\docs\design\4-上线检查清单.md`; `D:\Project\YunxiBakeBot\项目进度与配置清单.md`; `D:\Project\YunxiBakeBot\scripts\setup_wecom.sh`
- command: `rg -n "hclstudio\.cn|yunxifood\.cn" docs scripts 项目进度与配置清单.md LOGBOOK.md`
- result: pass
- related_logbook: 2026-06-17 - chore(release): 域名统一切换到 yunxifood.cn
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留文档变更和命令输出摘要；不包含密钥或证书内容
- summary: 后端发布文档、技术架构、有赞 webhook、管理后台子域、Nginx/certbot 示例与项目配置清单已统一到 `yunxifood.cn` / `admin.yunxifood.cn`；旧域名未在发布文档和脚本范围内残留。生产 HTTPS 与根入口已由 E-20260617-042 收口，微信公众平台和有赞云配置仍需复验。

## E-20260617-040：发布 readiness 总门槛

- trace_id: 20260617-release-readiness-gate
- generated_at: 2026-06-17
- evidence_type: release/command
- file: `D:\Project\YunxiBakeMiniApp\reports\release-readiness\readiness-20260617-092031.json`; `D:\Project\YunxiBakeMiniApp\reports\release-readiness\latest.json`; `D:\Project\YunxiBakeMiniApp\docs\release\manual-acceptance-checklist.md`
- command: `npm run release:readiness` in `YunxiBakeMiniApp`; `npm run check:addresses` in `web/admin`
- result: pass
- related_logbook: 2026-06-17 - test(release): 小程序发布 readiness 总门槛
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 JSON readiness 报告；报告不包含密钥或 Token
- summary: 新增发布前总检查入口和手工验收清单，最终 15/15 checks passed；覆盖小程序配置、静态/类型检查、后台结构检查、后端目标测试、关键 smoke 截图证据和临时数据库残留扫描；本机未发现微信开发者工具 CLI，开发者工具/真机/支付/审核材料仍需按清单补证据。

## E-20260617-039：手机端轻量运营入口

- trace_id: 20260617-mobile-ops-admin
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\mobile-operations-smoke.png`
- command: `python -m py_compile web\admin\scripts\smoke_mobile_operations.py`; `npm run check:mobile-ops`; `npm run typecheck` in `web/admin`; `npm run smoke:mobile-ops`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 手机端轻量运营入口
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 smoke 截图；临时 SQLite DB 按单文件规则清理，复查未发现 `mobile-operations-smoke.db*` 残留
- summary: 后台 Web 新增手机端轻量运营入口：统一导航配置、手机底栏高频入口、概览页手机运营快捷区，并通过移动视口 smoke 验证底栏可进入订单、商品、转人工、设置和概览。

## E-20260617-038：MVP 主链路巡检复跑

- trace_id: 20260617-mvp-main-flow-regression
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\decoration-product-picker-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\shop-settings-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\addresses-editing-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\orders-summary-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\orders-confirmation-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\products-active-toggle-smoke.png`; `D:\Project\YunxiBakeBot\reports\ui\transfers-queue-smoke.png`
- command: miniapp `npm run check:miniapp`; miniapp `npm run typecheck`; `npm run typecheck` in `web/admin`; `npm run check:decoration`; `npm run check:orders`; `npm run check:addresses`; `npm run check:products`; `npm run check:shop-settings`; `npm run smoke:decoration-product-picker`; `npm run smoke:shop-settings`; `npm run smoke:addresses-editing`; `npm run smoke:orders-summary`; `npm run smoke:orders-confirmation`; `npm run smoke:products-active-toggle`; `npm run smoke:transfers-queue`; backend API target pytest 40 passed; backend transfer pytest 15 passed
- result: pass
- related_logbook: 2026-06-17 - test(mvp): 主链路巡检复跑
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 smoke 截图；临时 SQLite DB 按单文件规则清理，复查未发现 `.db/.db-wal/.db-shm` 残留
- summary: 当前 MVP 主链路巡检通过，覆盖后台装修发布到小程序 JSON、店铺运营配置、顾客地址编辑、订单看板、订单状态流转、商品上下架、转人工队列、小程序静态/类型检查和后端 API 目标测试。

## E-20260617-037：后台人工回复 API 与转人工 smoke 收口

- trace_id: 20260617-admin-human-reply-api
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\transfers-queue-smoke.png`
- command: `python -m pytest -o addopts="" tests/api/test_admin_transfer_api.py tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py`; `python -m py_compile app\api\admin_transfer.py web\admin\scripts\smoke_transfers_queue.py tests\api\test_admin_transfer_api.py tests\service\test_miniapp_chat.py tests\api\test_miniapp_chat_api.py`; `npm run typecheck` in `web/admin`; `npm run smoke:transfers-queue`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 人工回复接口与转人工 smoke 收口
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 smoke 截图；临时 SQLite DB 按单文件规则清理
- summary: 后台转人工详情回复输入改为原生 textarea；后台人工回复 API 路由测试覆盖写入调用、空内容拒绝和会话消息返回；转人工浏览器 smoke 继续稳定覆盖入队、详情和接单。

## E-20260617-036：小程序人工回复刷新体验验证

- trace_id: 20260617-miniapp-human-reply-refresh
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py`; `python -m py_compile app\service\miniapp_chat.py tests\service\test_miniapp_chat.py tests\api\test_miniapp_chat_api.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 人工回复刷新体验
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告
- summary: 小程序客服页在转人工状态下新增等待提示、手动刷新和短轮询；后端服务测试证明后台人工回复以 `assistant` 写入后，小程序 `get_chat_payload` 能拉取展示。

## E-20260617-035：转人工队列浏览器 smoke

- trace_id: 20260617-transfers-queue-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\transfers-queue-smoke.png`
- command: `npm run smoke:transfers-queue`; `npm run typecheck` in `web/admin`; `python -m py_compile web\admin\scripts\smoke_transfers_queue.py`; `python -m pytest -o addopts="" tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py tests/test_lifespan_routes_services.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 转人工队列浏览器 smoke
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 smoke 截图；临时 SQLite DB 按单文件规则清理
- summary: 浏览器真实打开后台转人工页，验证小程序主动转人工 API 创建的待处理工单会出现在后台队列，详情抽屉可打开，后台可接单并更新为已接单。

## E-20260617-034：小程序客服主动转人工接口验证

- trace_id: 20260617-miniapp-chat-transfer
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py tests/test_lifespan_routes_services.py`; `python -m py_compile app\api\miniapp_chat.py app\service\miniapp_chat.py app\lifespan_services.py tests\service\test_miniapp_chat.py tests\api\test_miniapp_chat_api.py tests\test_lifespan_routes_services.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 用户主动转人工客服
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告
- summary: 小程序主动转人工接口复用既有转人工工单和后台队列；目标后端测试 13 passed，后端编译和小程序静态/类型检查均通过。

## E-20260617-033：订单经营看板浏览器 smoke

- trace_id: 20260617-admin-order-summary-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\orders-summary-smoke.png`
- command: `npm run smoke:orders-summary`; `npm run check:orders`; `npm run typecheck` in `web/admin`; `python -m py_compile web\admin\scripts\smoke_orders_summary.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 订单经营看板浏览器 smoke
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留 smoke 截图；临时 SQLite DB 按单文件规则清理
- summary: 浏览器真实打开后台订单页，验证全量 summary 卡片显示 3 笔测试订单，点击履约中和已关闭看板卡片后表格按后端 `boardFilter` 口径刷新。

## E-20260617-032：订单经营看板全量汇总

- trace_id: 20260617-admin-order-summary
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/api/test_admin_order_api.py`; `python -m py_compile app\api\admin_orders.py app\repository\order_repo.py app\service\miniapp_order.py tests\api\test_admin_order_api.py`; `npm run check:orders`; `npm run typecheck` in `web/admin`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 订单经营看板全量汇总
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后台订单新增 `GET /api/v1/admin/orders/summary` 全量聚合接口，订单列表支持 `boardFilter`，后台订单页看板读取后端 summary 并按同一口径加载列表。

## E-20260617-031：订单管理经营看板

- trace_id: 20260617-admin-order-board
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:orders`; `npm run typecheck` in `web/admin`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 订单管理经营看板
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后台订单页新增当前页经营看板，集中配置全部、待支付、待确认、履约中、已完成、已关闭口径，运营可点击看板卡片切换当前订单表格视图。

## E-20260617-030：订单状态事件驱动真实时间线

- trace_id: 20260617-order-status-events-timeline
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/api/test_admin_order_api.py tests/test_lifespan_routes_services.py`; `python -m py_compile app\models\order.py app\repository\order_event_repo.py app\repository\order_repo.py app\service\miniapp_order.py app\service\miniapp_order_serialization.py app\api\admin_orders.py app\api\miniapp_orders.py app\lifespan_services.py app\main.py app\migrations\schema.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py tests\api\test_admin_order_api.py tests\test_lifespan_routes_services.py`; `npm run check:orders`; `npm run typecheck` in `web/admin`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(order): 订单状态事件驱动真实时间线
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 新增 `order_events` 追加式订单状态事件表，创建订单、后台流转、用户取消、后台/超时关闭未支付都会追加事件；小程序订单详情和后台订单详情读取同一 `timeline` 字段展示真实节点时间。

## E-20260617-029：协议隐私售后统一配置

- trace_id: 20260617-shop-policy-config
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/api/test_shop_operations_api.py`; `python -m py_compile app\models\config.py app\service\shop_operations.py app\api\admin_config.py tests\api\test_shop_operations_api.py`; `npm run check:shop-settings`; `npm run typecheck` in `web/admin`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 协议隐私售后统一配置
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 店铺公开运营配置新增隐私政策、用户协议和售后说明标题/内容；后台店铺配置页可维护这些文案，小程序新增统一协议页，我的页可查看，checkout 提交前必须勾选同意用户协议和隐私政策。

## E-20260617-028：后台顾客地址操作审计

- trace_id: 20260617-admin-address-audit
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\addresses-editing-smoke.png`
- command: `python -m pytest -o addopts="" tests/api/test_admin_address_api.py tests/test_lifespan_routes_services.py`; `python -m py_compile app\api\admin_addresses.py app\service\miniapp_address.py app\repository\miniapp_address_audit_repo.py app\repository\miniapp_address_repo.py app\models\miniapp_address.py app\lifespan_services.py app\main.py tests\api\test_admin_address_api.py tests\test_lifespan_routes_services.py`; `npm run check:addresses`; `npm run typecheck` in `web/admin`; `npm run smoke:addresses-editing`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 顾客地址操作审计
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留浏览器成功截图和命令结论；临时 SQLite DB、WAL/SHM 已逐个清理；Chrome profile 目录按禁止递归删除规则未自动清理
- summary: 后台代顾客新增、编辑、设默认和删除小程序地址时写入 `miniapp_address_audit` 追加式审计，地址详情返回最近 5 条 `auditLogs`，后台详情抽屉展示“最近操作”；浏览器 smoke 覆盖新增、编辑、小程序地址读取和审计展示。

## E-20260617-027：我的页会员摘要配置驱动

- trace_id: 20260617-profile-member-config
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp`; `npm run typecheck` in `YunxiBakeMiniApp`; `npm run check:decoration`; `npm run typecheck` in `YunxiBakeBot\web\admin`; `python -m pytest -o addopts="" tests/service/test_shop_page_config.py tests/api/test_shop_page_config_api.py`; `python -m pytest` in `YunxiBakeBot`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 我的页会员摘要配置驱动
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 扩展 `memberSummary.props`，后台默认 profile 模板和装修编辑器可配置会员卡副标题、有效期、余额和权益卡数量；小程序我的页从装修配置读取这些字段并对旧配置兜底。

## E-20260617-026：小程序客服体验与后端测试补齐

- trace_id: 20260617-miniapp-chat-experience-tests
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp`; `npm run typecheck` in `YunxiBakeMiniApp`; `python -m pytest -o addopts="" tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py`; `python -m pytest` in `YunxiBakeBot`
- result: pass
- related_logbook: 2026-06-17 - chore(miniapp): 补齐客服体验与后端测试
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 小程序客服页保留欢迎消息兜底、加载失败提示、发送中状态和错误提示样式；后端新增小程序客服 service/API 测试，覆盖发送消息、历史拉取、用户头隔离、demo 用户回退和空消息拒绝。

## E-20260617-025：未支付超时自动关闭

- trace_id: 20260617-miniapp-payment-timeout-scheduler
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_admin_order_api.py tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\config.py app\repository\order_repo.py app\service\miniapp_order.py app\service\miniapp_payment.py app\service\miniapp_order_timeout.py app\api\admin_orders.py app\main.py tests\service\test_miniapp_order.py tests\api\test_admin_order_api.py`; architecture rg checks; `npm run check:orders`; `npm run typecheck` in `YunxiBakeBot\web\admin`; `npm run check:miniapp`; `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 未支付超时自动关闭
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后端新增未支付超时扫描器并在 lifespan 注册，后台可手动触发一次扫描；超过 30 分钟未支付订单会被关闭并释放真实商品库存，新订单和已支付订单不会被误关。

## E-20260617-024：订单支付状态 MVP 闭环

- trace_id: 20260617-miniapp-payment-state-mvp
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_admin_order_api.py tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\service\miniapp_payment.py app\service\miniapp_order.py app\api\miniapp_orders.py app\api\admin_orders.py tests\api\test_admin_order_api.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; architecture rg checks; `npm run check:orders`; `npm run typecheck` in `YunxiBakeBot\web\admin`; `npm run check:miniapp`; `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 订单支付状态 MVP 闭环
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 订单序列化输出支付状态字段，小程序可模拟支付确认，后台订单管理可展示支付状态并人工关闭未支付订单释放库存；批量超时关闭仍保留 30 分钟规则，真实微信支付后续接入同一状态字段。

## E-20260617-023：订单预约时间后端准入校验

- trace_id: 20260617-miniapp-order-expect-time-guard
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_shop_operations_api.py tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\service\business_hours.py app\service\shop_operations.py app\service\miniapp_order_schedule.py app\service\miniapp_order.py app\api\admin_config.py app\lifespan_services.py tests\api\test_shop_operations_api.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; architecture rg checks; miniapp check/typecheck; admin typecheck
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 订单预约时间后端准入校验
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后端创建小程序订单前校验 `expectTime` 格式和店铺 `businessHours`，非法预约时间返回 400 且不会先预占真实商品库存；营业时间解析、店铺运营配置读写和订单校验使用共享服务，后台配置 API 也会拒绝非法 `businessHours`。

## E-20260617-022：店铺营业时间格式校验

- trace_id: 20260617-admin-shop-business-hours-validation
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:shop-settings`; `npm run typecheck` in `web/admin`; `python -m pytest --no-cov tests/api/test_shop_operations_api.py`; `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 店铺营业时间格式校验
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后台店铺配置页保存前校验 `businessHours` 格式，避免小程序 checkout 时间选择器收到不可解析配置；后台结构检查、类型检查、店铺配置 API 测试和小程序检查均通过。

## E-20260617-021：Checkout 时间选择联动后台营业时间

- trace_id: 20260617-miniapp-checkout-business-hours
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`; `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-17 - chore(miniapp): Checkout 时间选择联动后台营业时间
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: checkout 时间 picker 的小时选项由小程序公开店铺配置 `businessHours` 生成，后台调整营业时间后小程序下单时段可同步收口。

## E-20260617-020：Checkout 期望时间升级为日期时间选择器

- trace_id: 20260617-miniapp-checkout-time-picker
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`; `python -m py_compile app\api\miniapp_orders.py app\service\miniapp_order.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-17 - chore(miniapp): Checkout 期望时间升级为日期时间选择器
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: checkout 使用原生 picker 生成稳定格式期望时间，并抽出时间工具，后续可接后台营业时间配置；小程序和后台类型/静态检查通过。

## E-20260617-019：Checkout 增强表单校验与提示

- trace_id: 20260617-miniapp-checkout-form-validation
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`; `python -m py_compile app\api\miniapp_orders.py app\service\miniapp_order.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-17 - chore(miniapp): Checkout 增强表单校验与提示
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: checkout 页面新增手机号、配送地址、期望时间的前置校验，并将错误稳定展示在页面内；小程序和后台类型/静态检查通过。

## E-20260617-018：Checkout 展示后端下单失败原因

- trace_id: 20260617-miniapp-checkout-error-feedback
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_miniapp_order_api.py tests/service/test_miniapp_order.py`; `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`; `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-17 - chore(miniapp): Checkout 展示后端下单失败原因
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后端订单 API/service 测试确认库存错误语义仍稳定；小程序 HTTP 层会保留后端 `detail/message`，checkout 页面将具体错误展示给用户并禁用重复提交。

## E-20260617-017：小程序用户取消订单并释放库存

- trace_id: 20260617-miniapp-order-user-cancel
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\api\miniapp_orders.py app\service\miniapp_order.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; architecture `rg` checks; `npm run typecheck` in `web/admin`; `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 小程序用户取消订单并释放库存
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 后端服务/API 测试覆盖用户取消自己的待确认/已确认订单并释放真实商品库存、制作中不可取消、不能取消他人订单；小程序订单详情页加入取消按钮，小程序和后台类型/静态检查通过。

## E-20260617-016：小程序真实商品库存预占与取消释放

- trace_id: 20260617-miniapp-order-stock-reservation
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\repository\youzan_inventory_repo.py app\service\miniapp_order_inventory.py app\service\miniapp_order.py app\lifespan_services.py app\main.py tests\service\test_miniapp_order.py tests\api\test_miniapp_order_api.py`; architecture `rg` checks; `npm run typecheck` in `web/admin`; `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 小程序真实商品库存预占与取消释放
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告文件
- summary: 服务/API 测试覆盖真实商品下单扣减库存、取消订单释放库存、重复商品项合并后按总数量校验库存；架构扫描确认 API 不穿透仓储、service 不直连数据库；小程序和后台类型/静态检查通过。

## E-20260617-015：小程序下单真实商品库存校验

- trace_id: 20260617-miniapp-order-stock-guard
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/service/test_miniapp_order.py tests/api/test_miniapp_order_api.py tests/repository/test_youzan_repo.py`; `python -m py_compile app\repository\youzan_repo.py app\service\miniapp_order.py app\api\miniapp_orders.py tests\api\test_miniapp_order_api.py tests\service\test_miniapp_order.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`; admin `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 小程序下单接入真实商品库存校验
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；本轮未创建临时 DB/截图产物
- summary: 小程序创建订单时，如果商品存在于后端商品宽表，则以宽表价格、库存和上下架状态为准；服务和 API 测试覆盖库存充足使用后端价格、库存不足返回 400、售罄拒绝、下架拒绝，并保留未入库 Mock/fallback 商品下单能力。

## E-20260617-014：小程序下单到后台完整履约 smoke

- trace_id: 20260617-admin-orders-confirmation-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\orders-confirmation-smoke.png`
- command: `npm run smoke:orders-confirmation`; `npm run check:orders`; backend admin `npm run typecheck`; `python -m pytest --no-cov tests/service/test_miniapp_order.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 小程序下单到后台完整履约 smoke 跑通
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图与命令结论；临时 SQLite DB 与失败调试截图已逐个删除
- summary: 通过小程序订单 API 创建测试订单，真实浏览器打开后台订单管理页并依次点击“确认订单、开始制作、配送中、完成”，小程序订单详情 API 每一步读取到 `confirmed`、`making`、`delivering`、`done`，最终后台订单详情抽屉显示已完成，证明用户下单、后台履约、用户侧状态读取这条 MVP 订单主链路可联通。

## E-20260617-013：后台商品上下架驱动小程序目录 smoke

- trace_id: 20260617-admin-products-active-toggle-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\products-active-toggle-smoke.png`
- command: `npm run smoke:products-active-toggle`; `npm run smoke:decoration-product-picker`; `npm run check:products`; `npm run check:decoration`; backend admin `npm run typecheck`; `python -m pytest --no-cov tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py tests/service/test_miniapp_catalog.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 商品上下架驱动小程序目录 smoke 跑通
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图与命令结论；临时 SQLite DB 与失败调试截图已逐个删除；既有 Chrome profile 目录按禁止递归删除规则未自动清理
- summary: 真实浏览器操作后台商品管理页，搜索测试商品 `smoke active cheesecake`，执行下架后小程序 `/api/v1/miniapp/products?ids=92017004` 不再返回该商品；再在已下架筛选中执行上架后，小程序商品接口恢复返回该商品。共享 smoke 工具同时回归通过装修商品选择器链路。

## E-20260617-012：后台装修商品选择器浏览器 smoke

- trace_id: 20260617-admin-decoration-product-picker-smoke
- generated_at: 2026-06-17
- evidence_type: screenshot/command
- file: `D:\Project\YunxiBakeBot\reports\ui\decoration-product-picker-smoke.png`
- command: `npm run smoke:decoration-product-picker` in `YunxiBakeBot\web\admin`; `npm run check:decoration`; backend admin `npm run typecheck`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 装修商品选择器浏览器 smoke 跑通
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图与命令结论；临时 SQLite DB 与失败调试截图已逐个删除；既有 Chrome profile 目录按禁止递归删除规则未自动清理
- summary: 真实浏览器通过后台装修页切换到商品页货架模块，打开商品选择器，搜索测试商品 `smoke picker strawberry cake`，执行保存草稿和发布；随后小程序 `/api/v1/miniapp/pages/products` published 配置读取到 `productIds=["91017003"]`，证明后台装修生产的 JSON 配置能驱动小程序端读取。

## E-20260617-011：后台装修自动化选择器结构验证

- trace_id: 20260617-admin-decoration-testids
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:decoration` and `npm run typecheck` in `YunxiBakeBot\web\admin`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py`; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 装修页补稳定自动化选择器
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 店铺装修页关键操作点补充稳定 `data-testid`、`data-block-id` 和 `data-product-id`，覆盖页面选择、保存发布、模块卡片、已选商品区、选品弹窗、搜索和加入商品按钮；装修结构检查已纳入这些自动化选择器，便于后续 Playwright/CDP smoke 直接按稳定选择器执行。

## E-20260617-010：后台装修已选商品名称展示与商品链路验证

- trace_id: 20260617-admin-decoration-selected-product-titles
- generated_at: 2026-06-17
- evidence_type: command/api
- file: local command output (no persisted artifact)
- command: 使用本地临时 SQLite DB 启动后端 `127.0.0.1:7001` 和后台 Vite `127.0.0.1:5173`，种入 `smoke picker strawberry cake`，通过后台商品搜索 API 命中 `youzan_item_id=91017003`，再保存并发布 `products` 页面装修草稿，最后用小程序 `/api/v1/miniapp/pages/products` 校验 `productIds=["91017003"]`；随后运行 `npm run check:decoration`、后台 `npm run typecheck`、装修 API/service 测试、小程序静态检查和小程序 typecheck
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修商品货架已选商品显示名称
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；临时 SQLite DB、一次性 Chrome CDP 调试脚本已逐个删除；Chrome 点击专项未形成通过截图证据
- summary: 店铺装修页商品货架已选区新增商品名称缓存和展示，选品列表加载或加入商品时复用后台商品列表数据，已选标签优先显示商品名并保留商品 ID 辅助识别；API smoke 证明后台商品搜索、装修草稿保存、发布和小程序页面配置读取能围绕同一个商品 ID 串起来。

## E-20260617-009：后台装修分类与服务入口浏览器 smoke

- trace_id: 20260617-admin-decoration-grid-link-editor
- generated_at: 2026-06-17
- evidence_type: screenshot
- file: `D:\Project\YunxiBakeBot\reports\ui\admin-decoration-grid-link-smoke.png`
- command: 使用临时 SQLite DB 启动本地后端 `127.0.0.1:7001`、后台 Vite `127.0.0.1:5173`、headless Chrome CDP `127.0.0.1:9224`；浏览器进入 `/admin-v2/decoration`，切换到 `products` 页面通过分类宫格表单发布 `smoke-category-a-202606170121`、`smoke-category-b-202606170121`，再切换到 `profile` 页面通过服务入口表单发布 `smoke-service-title-202606170121` 和 `smoke-service-target-202606170121`；随后调用小程序页面 API 核对 published 配置
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修分类与服务入口支持结构化编辑
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图与本地 smoke 命令结论；临时 SQLite DB、一次性 smoke 脚本和调试脚本已逐个删除；既有 Chrome profile 目录按禁止递归删除规则未自动清理
- summary: 浏览器真实操作证明后台装修页的分类宫格、服务入口结构化表单可保存并发布；小程序 `/api/v1/miniapp/pages/products` 和 `/api/v1/miniapp/pages/profile` 读取到发布后的分类 ID、服务入口标题和跳转目标。

## E-20260617-008：后台装修分类与服务入口结构化编辑验证

- trace_id: 20260617-admin-decoration-grid-link-editor
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:decoration` and `npm run typecheck` in `YunxiBakeBot\web\admin`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py`; architecture rg checks; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修分类与服务入口支持结构化编辑
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 店铺装修页为 `categoryGrid` 增加分类 ID 多行表单，为 `quickLinks` 和 `serviceGrid` 增加模块标题、入口增删、图标文字、跳转类型和跳转目标表单；新增结构检查脚本防止关键模块退回 JSON-only。

## E-20260617-007：后台装修多页面切换浏览器 smoke

- trace_id: 20260617-admin-decoration-page-switcher
- generated_at: 2026-06-17
- evidence_type: screenshot
- file: `D:\Project\YunxiBakeBot\reports\ui\admin-decoration-page-switcher-smoke.png`
- command: 使用临时 SQLite DB 启动本地后端 `127.0.0.1:7001`、后台 Vite `127.0.0.1:5173`、headless Chrome CDP `127.0.0.1:9224`；浏览器进入 `/admin-v2/decoration`，切换到 `products` 页面，修改商品货架标题为 `smoke-products-shelf-20260617010822`，保存草稿并发布；随后调用 `/api/v1/miniapp/pages/products` 核对小程序 published 配置
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修编辑器支持多页面切换
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图与本地 smoke 命令结论；临时 SQLite DB、一次性 smoke 脚本和调试脚本已逐个删除；Chrome profile 目录按禁止递归删除规则未自动清理
- summary: 浏览器真实操作证明后台装修页可切换到商品页、编辑模块配置、保存草稿并发布；保存草稿时小程序 published 仍保持旧标题，发布后小程序页面配置读取到新标题。

## E-20260617-006：后台装修多页面切换验证

- trace_id: 20260617-admin-decoration-page-switcher
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py`; `python -m py_compile app\service\shop_page_config.py tests\api\test_shop_page_config_api.py tests\service\test_shop_page_config.py`; `npm run typecheck` in `YunxiBakeBot\web\admin`; architecture rg checks; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修编辑器支持多页面切换
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 后台装修编辑器新增页面选择器，加载、刷新、保存草稿和发布均按当前页面 ID 调用既有装修 API；默认页面配置拆分为 `home`、`products`、`profile` 三套模块，并通过服务和 API 测试覆盖。

## E-20260617-005：后台装修商品选择弹窗分页验证

- trace_id: 20260617-admin-decoration-product-picker-pagination
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run typecheck` and `npm run build` in `YunxiBakeBot\web\admin`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py`; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修商品选择弹窗补齐分页
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；`web/admin/dist/` 为 build 生成的忽略目录，按项目禁止递归删除规则未自动清理
- summary: 店铺装修商品选择弹窗补齐当前页、总数和页大小状态；搜索时重置到第一页，翻页时复用既有商品列表接口加载对应页；弹窗底部展示分页条和在售商品总数。

## E-20260617-004：后台装修商品货架弹窗选品验证

- trace_id: 20260617-admin-decoration-product-picker
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run typecheck` and `npm run build` in `YunxiBakeBot\web\admin`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py`; architecture rg checks; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 装修商品货架支持弹窗选品
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；`web/admin/dist/` 为 build 生成的忽略目录，按项目禁止递归删除规则未自动清理
- summary: 店铺装修的商品货架模块新增商品选择弹窗，复用后台商品列表服务搜索在售商品，展示商品名、ID、编码、价格和库存，选中后写回 `productShelf.props.productIds`；已选商品以标签展示并可移除，仍保留文本批量编辑。弹窗分页已在 `20260617-admin-decoration-product-picker-pagination` 补齐。

## E-20260617-003：后台装修结构化编辑器验证

- trace_id: 20260617-admin-decoration-structured-editor
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run typecheck` and `npm run build` in `YunxiBakeBot\web\admin`; `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py`; architecture rg checks; `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - feat(admin): 店铺装修编辑器改为结构化表单
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；`web/admin/dist/` 为 build 生成的忽略目录，按项目禁止递归删除规则未自动清理
- summary: 后台店铺装修页从单一 `Props JSON` 文本框升级为结构化表单，覆盖搜索、公告、轮播、商品货架、富文本、会员横幅、会员摘要和须知列表；保留高级 JSON 兜底，并扩展手机预览覆盖主要模块。

## E-20260617-002：小程序商品图片后端受控代理验证

- trace_id: 20260617-miniapp-image-proxy-chain
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py tests/service/test_miniapp_catalog.py tests/api/test_shop_operations_api.py tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py tests/service/test_admin.py`; `python -m py_compile app\api\miniapp_catalog.py app\service\miniapp_catalog.py tests\api\test_miniapp_catalog_api.py tests\service\test_miniapp_catalog.py`; architecture rg checks; miniapp static/type checks; admin typecheck
- result: pass
- related_logbook: 2026-06-17 - feat(catalog): 小程序商品图片改为后端受控代理
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 商品 API `imageUrl` 返回后端同域代理路径，小程序商品 service 统一补全 `API_BASE_URL`；新增 `/api/v1/miniapp/products/{product_id}/image` 按商品 ID 查询已上架商品图片并校验协议、图片类型和大小；测试覆盖代理成功、无图、缺失商品和非法协议拒绝。

## E-20260617-001：小程序商品 API 有赞图片透传验证

- trace_id: 20260617-miniapp-product-images-chain
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py tests/service/test_miniapp_catalog.py tests/api/test_shop_operations_api.py tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py tests/service/test_admin.py`; architecture rg checks; miniapp static/type checks; admin typecheck
- result: pass
- related_logbook: 2026-06-17 - feat(catalog): 小程序商品 API 透传有赞商品图片
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 商品目录仓储从 `youzan_products.image` 读取图片并挂载为 `image_url`，小程序商品 API 输出契约字段 `imageUrl`；服务级和 API 级测试覆盖商品列表、装修货架、主推商品和详情图片字段。

## E-20260616-017：后台主推商品页面浏览器保存 smoke

- trace_id: 20260616-admin-featured-browser-smoke
- generated_at: 2026-06-16
- evidence_type: screenshot
- file: `D:\Project\YunxiBakeBot\reports\ui\admin-featured-products-smoke.png`
- command: 使用临时 SQLite DB 启动本地后端 `127.0.0.1:7001`、后台 Vite `127.0.0.1:5173`、headless Chrome CDP `127.0.0.1:9223`；浏览器打开 `/admin/products/featured`，搜索 `烟测`，添加两条候选商品，保存主推款，并调用 `/api/v1/miniapp/products?featured=true` 核对小程序公开商品列表；随后运行商品/主推后端测试、分层红线搜索、小程序静态/type checks、后台 typecheck。
- result: pass
- related_logbook: 2026-06-16 - test(admin): 浏览器验证主推商品页面保存链路
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留截图和本地 smoke 日志；临时 SQLite DB 已逐个删除；本地服务已停止
- summary: 浏览器真实操作证明后台主推商品页面可搜索候选商品、添加主推、保存配置；保存后小程序 featured 商品接口按同一顺序返回 `烟测草莓奶油蛋糕`、`烟测芒果千层`。

## E-20260616-016：后台主推商品到小程序 featured 链路验证

- trace_id: 20260616-admin-featured-catalog-chain
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_admin_featured_catalog_api.py tests/api/test_miniapp_catalog_api.py tests/service/test_miniapp_catalog.py tests/api/test_shop_operations_api.py tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py tests/service/test_admin.py`; architecture rg checks; miniapp static/type checks; admin typecheck
- result: pass
- related_logbook: 2026-06-16 - test(catalog): 打通后台主推到小程序 featured 商品
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 新增跨路由测试证明后台 `/api/v1/admin/shop-config/featured-products` 保存主推商品并清理空白值后，后台商品列表 `featured_only=true` 和小程序 `/api/v1/miniapp/products?featured=true` 都按同一配置顺序返回主推商品。

## E-20260616-015：小程序商品目录 API 链路验证

- trace_id: 20260616-miniapp-catalog-api-chain
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_miniapp_catalog_api.py tests/service/test_miniapp_catalog.py tests/api/test_shop_operations_api.py tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py`; architecture rg checks; miniapp static/type checks; admin typecheck
- result: pass
- related_logbook: 2026-06-16 - test(catalog): 补小程序商品目录 API 链路验证
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 新增 `tests/api/test_miniapp_catalog_api.py`，证明小程序公开商品 API 可读取在售商品，装修货架 `ids` 按配置顺序返回并跳过无效/重复商品，后台主推标题配置可驱动 `featured=true`，商品详情可按有赞 item_id 读取。

## E-20260616-014：店铺运营配置 API 联动验证

- trace_id: 20260616-shop-operations-api-chain
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_shop_operations_api.py tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py`; `python -m py_compile tests\api\test_shop_operations_api.py`; architecture rg checks; miniapp/admin type checks
- result: pass
- related_logbook: 2026-06-16 - test(shop): 补店铺运营配置 API 联动验证
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 新增 API 路由级测试证明后台店铺运营配置接口会校验管理员 Token，保存店铺名称、客服微信、客服电话、营业时间、自提和配送说明后，小程序 `/api/v1/miniapp/shop-settings` 读取同一份公开配置。

## E-20260616-013：后台装修 API 路由级验证

- trace_id: 20260616-decoration-api-chain
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/api/test_shop_page_config_api.py tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py`; `python -m py_compile tests\api\test_shop_page_config_api.py tests\service\test_shop_page_config.py`
- result: pass
- related_logbook: 2026-06-16 - test(decoration): 补装修 API 路由级验证
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 新增 API 路由级测试证明后台装修接口会校验管理员 Token，保存草稿后小程序仍读取旧 published 配置，发布后小程序读取最新页面配置。

## E-20260616-011：后台装修发布链路服务级验证

- trace_id: 20260616-decoration-publish-chain
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest --no-cov tests/service/test_shop_page_config.py tests/service/test_miniapp_order.py`; `python -m py_compile app\service\shop_page_config.py tests\service\test_shop_page_config.py`; architecture rg checks; miniapp/admin type checks
- result: pass
- related_logbook: 2026-06-16 - test(decoration): 验证装修草稿发布到小程序
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 新增服务级测试证明后台保存装修草稿不会影响小程序 published 配置；发布后小程序读取到最新商品货架配置；无草稿时可发布默认配置，保证初始化后小程序可渲染。

## E-20260616-012：后台装修发布链路浏览器烟测

- trace_id: 20260616-decoration-publish-chain
- generated_at: 2026-06-16
- evidence_type: screenshot
- file: `D:\Project\YunxiBakeBot\reports\ui\admin-decoration-publish-smoke.png`
- command: Chrome 远程调试打开 `/admin-v2/login?redirect=%2Fadmin-v2%2Fdecoration`，登录后在装修页修改商品货架标题、保存草稿、发布，并通过 API 核对小程序 published 配置
- result: pass
- related_logbook: 2026-06-16 - test(decoration): 验证装修草稿发布到小程序
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留浏览器截图；临时 Chrome profile 仅用于本次烟测
- summary: 浏览器真实操作证明后台装修编辑器可登录、可修改模块 JSON、可保存草稿、可发布；保存后小程序仍读取旧 published 配置，发布后小程序读取新标题。

## E-20260616-010：小程序页面静态一致性检查

- trace_id: 20260616-miniapp-static-page-check
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run check:miniapp`; `npm run typecheck` in `YunxiBakeMiniApp`; JSON parsing for miniapp config; `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-16 - test(miniapp): 增加页面静态一致性检查
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论
- summary: 小程序页面四件套、路由常量、tabBar 跳转、WXML 事件绑定和顶层 data 引用检查通过；订单详情页返回订单列表已修正为 `switchTab`。

## E-20260616-009：订单履约完整状态链 API 验证

- trace_id: 20260616-order-status-chain-smoke
- generated_at: 2026-06-16
- evidence_type: api
- file: local command output (no persisted artifact)
- command: local HTTP smoke for miniapp order create, admin status updates, miniapp order detail/list reads
- result: pass
- related_logbook: 2026-06-16 - test(order): 验证履约完整状态链
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；临时本地服务已停止
- summary: 订单 `mp_20260616210530_72f31260` 完成 `pending -> confirmed -> making -> delivering -> done` 状态链验证；小程序详情每一步读取到最新状态；非法 `pending -> done` 和 `done -> cancelled` 均被 400 拒绝。

## E-20260616-008：小程序订单状态联动 API 验证

- trace_id: 20260616-miniapp-admin-status-sync-smoke
- generated_at: 2026-06-16
- evidence_type: api
- file: local command output (no persisted artifact)
- command: local HTTP smoke for `/api/v1/miniapp/auth/login`, `/api/v1/miniapp/pages/home`, `/api/v1/miniapp/shop-settings`, `/api/v1/miniapp/orders`, `/api/v1/admin/orders/{order_id}/status`, `/api/v1/miniapp/orders/{order_id}`
- result: pass
- related_logbook: 2026-06-16 - test(miniapp): 验证小程序订单状态联动
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论；临时本地服务已停止
- summary: 本地创建小程序订单 `mp_20260616210101_c9e57450`，后台将状态从 `pending` 更新为 `confirmed`，小程序订单详情和列表均读取到 `confirmed`。

## E-20260616-007：后台订单与店铺配置交互验证

- trace_id: 20260616-admin-interaction-smoke
- generated_at: 2026-06-16
- evidence_type: screenshot
- file: `reports/ui/admin-order-detail-drawer-smoke.png`; `reports/ui/admin-order-confirmed-smoke.png`; `reports/ui/admin-shop-settings-save-smoke.png`
- command: Chrome DevTools smoke for `/admin/orders?status=pending` and `/admin/settings/shop`
- result: pass
- related_logbook: 2026-06-16 - test(admin): 验证订单履约与店铺配置交互
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留浏览器截图；临时本地服务已停止；店铺名称已恢复原值
- summary: 后台订单详情抽屉可打开，待确认订单可通过页面操作更新为已确认；店铺配置可通过页面保存，并已通过 API 恢复原店名“芸熙烘焙”。

## E-20260616-006：后台设置摘要 MiMo 字段与本地路由收口验证

- trace_id: 20260616-admin-overview-mvp
- generated_at: 2026-06-16
- evidence_type: command / screenshot
- file: `reports/ui/admin-overview-smoke.png`; `reports/ui/admin-settings-api-smoke.png`; `reports/ui/admin-orders-pending-smoke.png`
- command: `rg -n "webhookTokenConfigured|deepseek|DeepSeek" web/admin/src app/service/admin.py app/api/admin_config.py app/models/config.py`; `npm run typecheck` and `npm run build` in `web/admin`; `python -m py_compile` for miniapp/admin MVP modules; architecture rg checks; Chrome DevTools smoke for `/admin/overview`, `/admin/settings/api`, `/admin/orders?status=pending`
- result: pass
- related_logbook: 2026-06-16 - fix(admin): 收口设置摘要 MiMo 字段引用和后台本地路由
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留浏览器截图和命令结论；临时本地服务已停止
- summary: 后台概览不再引用已移除的有赞 webhook token 和 DeepSeek 字段；Vite dev server 不再把 `/admin` 代理到后端，后台 SPA 路由可正常打开；概览、API 设置和待确认订单深链通过浏览器渲染 smoke。

## 登记模板

```markdown
## E-YYYYMMDD-001：标题

- trace_id:
- generated_at:
- evidence_type: handoff | preflight | smoke | migration | seed | embedding | review | other
- file:
- command:
- result: pass | fail | partial
- related_logbook:
- related_adr:
- contains_sensitive_data: yes | no
- retention_note:
- summary:
```

______________________________________________________________________

## 当前证据

## E-20260617-010：后台店铺配置保存到小程序公开配置 smoke

- trace_id: 20260617-admin-shop-settings-smoke
- generated_at: 2026-06-17
- evidence_type: smoke
- file: `D:\Project\YunxiBakeBot\reports\ui\shop-settings-smoke.png`
- command: `npm run smoke:shop-settings`; `npm run smoke:orders-confirmation`; `npm run smoke:products-active-toggle`; `npm run smoke:decoration-product-picker`; `npm run check:shop-settings`; `npm run check:products`; `npm run check:orders`; `npm run check:decoration`; `npm run typecheck` in `web/admin`; `python -m pytest --no-cov tests/api/test_shop_operations_api.py`; miniapp `npm run check:miniapp`; miniapp `npm run typecheck`
- result: pass
- related_logbook: 2026-06-17 - test(admin): 店铺配置保存到小程序公开配置 smoke 跑通
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留浏览器成功截图和命令结论；临时 SQLite DB、WAL/SHM 和失败截图已逐个清理
- summary: 浏览器真实操作后台店铺配置页填写并保存店铺名称、电话、微信、营业时间、自提和配送说明后，小程序 `GET /api/v1/miniapp/shop-settings` 读取到同一份公开配置；订单确认、商品上下架、装修选品 smoke 顺序复跑通过，确认共享 smoke 工具调整没有破坏既有链路。

## E-20260616-006：后台商城经营台概览验证

- trace_id: 20260616-admin-overview-mvp
- generated_at: 2026-06-16
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `npm run typecheck` in `web/admin`
- result: pass
- related_logbook: 2026-06-16 - feat(admin): 将后台概览改造成商城经营台
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时脚本文件
- summary: 后台概览重构后通过类型检查，订单列表 query 深链联动可用。

## E-20260617-001：小程序客服主动转人工接口验证

- trace_id: 20260617-miniapp-chat-transfer
- generated_at: 2026-06-17
- evidence_type: command
- file: local command output (no persisted artifact)
- command: `python -m pytest -o addopts="" tests/service/test_miniapp_chat.py tests/api/test_miniapp_chat_api.py tests/test_lifespan_routes_services.py`; `python -m py_compile app\api\miniapp_chat.py app\service\miniapp_chat.py app\lifespan_services.py tests\service\test_miniapp_chat.py tests\api\test_miniapp_chat_api.py tests\test_lifespan_routes_services.py`; `npm run check:miniapp` and `npm run typecheck` in `YunxiBakeMiniApp`
- result: pass
- related_logbook: 2026-06-17 - feat(miniapp): 用户主动转人工客服
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时报告
- summary: 小程序主动转人工接口复用既有转人工工单和后台队列；目标后端测试 13 passed，后端编译和小程序静态/类型检查均通过。

## E-20260616-005：小程序订单详情接口类型与分层验证

- trace_id: 20260616-miniapp-order-detail-mvp
- generated_at: 2026-06-16
- evidence_type: smoke
- file: local command output (no persisted report)
- command: `python -m py_compile app\service\miniapp_order.py app\api\miniapp_orders.py`; `npm run typecheck` in `YunxiBakeMiniApp`; architecture rg checks
- result: pass
- related_logbook: 2026-06-16 - feat(miniapp): 新增小程序订单详情接口
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时脚本文件
- summary: 小程序订单详情接口和页面通过类型/编译检查，API 层未直接穿透 repository，service 层未直连数据库。

## E-20260616-004：店铺运营配置类型与分层验证

- trace_id: 20260616-shop-operations-config-mvp
- generated_at: 2026-06-16
- evidence_type: smoke
- file: local command output (no persisted report)
- command: `python -m py_compile app\models\config.py app\service\admin.py app\api\admin_config.py`; `npm run typecheck` in `web/admin`; `npm run typecheck` in `YunxiBakeMiniApp`; architecture rg checks
- result: pass
- related_logbook: 2026-06-16 - feat(miniapp/admin): 接入店铺运营配置 MVP
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时脚本文件
- summary: 店铺运营配置后端 API、后台表单和小程序读取层均通过类型/编译检查，架构红线搜索无输出。

## E-20260616-003：后台订单履约状态服务级验证

- trace_id: 20260616-admin-order-fulfillment-mvp
- generated_at: 2026-06-16
- evidence_type: smoke
- file: local command output (no persisted report)
- command: `python -m py_compile app\repository\order_repo.py app\service\miniapp_order.py app\api\admin_orders.py`; `npm run typecheck` in `web/admin`; inline Python service smoke for `MiniappOrderService.update_admin_order_status`
- result: pass
- related_logbook: 2026-06-16 - feat(admin): 补齐小程序订单履约处理 MVP
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留命令结论，不保留临时脚本文件
- summary: 后台订单详情和状态更新代码可编译，后台前端类型检查通过，服务级 smoke 验证待确认可切换到已确认且非法越级切换会被拒绝。

## E-20260616-002：小程序完整 MVP 本地 API smoke

- trace_id: 20260616-miniapp-mvp-smoke
- generated_at: 2026-06-16
- evidence_type: smoke
- file: local command output (no persisted report)
- command: `python -m uvicorn app.main:app --host 127.0.0.1 --port 7010` 后，用 `Invoke-RestMethod` 依次验证 `/health`、`/api/v1/miniapp/auth/login`、`/api/v1/miniapp/pages/home`、`/api/v1/miniapp/products`、`/api/v1/miniapp/chat/messages`、`/api/v1/miniapp/orders`、`/api/v1/admin/orders`
- result: pass
- related_logbook: 2026-06-16 - feat(miniapp): 接入小程序登录会话 MVP / feat(miniapp): 接入小程序客服消息 API / feat(miniapp/admin): 接入小程序订单草稿和后台订单列表
- related_adr: none
- contains_sensitive_data: no
- retention_note: 仅保留 smoke 结论，不保留临时日志文件
- summary: 登录、装修、客服、订单和后台订单列表接口联通成功；本地商品表未命中示例商品 ID，商品接口返回空列表，说明前端仍需 Mock 兜底。

## E-20260616-001：有赞客服托管连通性测试交接快照

- trace_id: YZ-HOSTING-CONNECTIVITY-20260616
- generated_at: 2026-06-16
- evidence_type: handoff
- file: reports/harness/youzan-hosting-connectivity-20260616.md
- command: `python scripts/harness_snapshot.py --trace-id YZ-HOSTING-CONNECTIVITY-20260616 --goal "有赞客服托管与现有 AI 客服收发连通性测试" --status completed --output reports/harness/youzan-hosting-connectivity-20260616.md`
- result: pass
- related_logbook: 2026-06-16 - feat(youzan): 接入客服托管收发连通性测试
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留本次连通性测试与分层边界决策依据，便于后续有赞订阅联调和回归排障。
- summary: 记录有赞客服托管消息分流、托管回复 API、异步 webhook 测试与数据库零改造判断。

## E-20260620-001：有赞客户正式迁移与后验核对闭环

- trace_id: 20260620-customer-import-pipeline
- generated_at: 2026-06-20
- evidence_type: handoff/runbook/command
- file: `D:\Project\YunxiBakeBot\reports\harness\customer-import-pipeline-20260620.md`; `D:\Project\YunxiBakeBot\docs\architecture\youzan-customer-formal-import-runbook.md`; `D:\Project\YunxiBakeBot\scripts\import_youzan_customers.py`; `D:\Project\YunxiBakeBot\scripts\verify_youzan_customer_import.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_import_youzan_customers.py`; `D:\Project\YunxiBakeBot\tests\scripts\test_verify_youzan_customer_import.py`
- command: `python scripts/import_youzan_customers.py --customer-csv "docs\有赞导出\客户数据_0002000408539943.csv" --orders-csv "docs\有赞导出\订单数据.csv" --db-path "data\bot.db" --tenant-id "yunxi" --source-batch-id "youzan-customer-20260620-full" --apply --json --output "reports\youzan-customer-import-apply-{timestamp}.json"`; `python scripts/verify_youzan_customer_import.py --db-path "data\bot.db" --tenant-id "yunxi" --source-batch-id "youzan-customer-20260620-full" --import-report "reports\youzan-customer-import-apply-20260620-120000.json" --json --output "reports\youzan-customer-import-verify-{timestamp}.json"`; `python scripts/harness_snapshot.py --trace-id 20260620-customer-import-pipeline --goal "接着做" --status completed --output reports/harness/customer-import-pipeline-20260620.md`
- result: pass
- related_logbook: 2026-06-20 - feat(customer): 新增正式迁移后批次核对脚本; 2026-06-20 - docs(customer): 补齐正式客户迁移执行 runbook; 2026-06-20 - feat(customer): 新增正式有赞客户迁移入口脚本
- related_adr: none
- contains_sensitive_data: no
- retention_note: 保留正式迁移、后验核对与交接快照的摘要索引；实际 JSON 报告与数据库快照按 reports/ 目录管理，不在索引中重复记录敏感内容。
- summary: customer 域正式迁移已经从“审计”推进到“dry-run / apply / 后验核对 / 交接快照”四段闭环；交接快照与证据索引已可直接用于后续补跑和换手。
