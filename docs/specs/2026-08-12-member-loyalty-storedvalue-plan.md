# 会员储值/积分/优惠券账务域可执行计划书

- 状态：执行中
- trace_id：`20260812-member-loyalty-storedvalue`
- 来源：迁移前功能补齐盘点。当前"我的"页面会员卡数据为静态假数据（`shop_page_config.py` 中 balanceFen=0, points=0, coupons=0），无真实账务域。
- 前置依赖：微信支付商户号（阻塞，先 mock 跑通）
- 消息推送：✅ 已订阅
- 数据策略：全量导入打底 + Webhook 增量维持（同 openid 预导入模式）

## 目标

实现会员储值余额、积分、优惠券完整闭环。商户号到位后切换一行配置即可。

---

## 已订阅事件

| 事件 | msg 核心字段 | 写入目标 |
|------|-------------|---------|
| SCRM_CUSTOMER_EVENT | mobile, name, is_member, status(CREATED/UPDATED) | 客户身份更新 |
| POINTS | amount, total, event_type, yz_open_id, mobile, unique_id | `points_ledger` |
| COUPON_CUSTOMER_PROMOTION | id, status(TAKE/CONSUME/BACK), mobile, coupon_group_id, order_no | `coupon_inventory`（反查券详情补全） |
| SCRM_CUSTOMER_CARD | card_alias, card_no, mobile, yz_open_id, status | 会员卡状态 |

---

## 里程碑

### M1：数据底座（3 天）

| # | 任务 |
|---|------|
| 1.1 | `event_member.py`：解析四种事件 msg，按 type 分发处理 |
| 1.2 | `event_handler.py` 新增路由分支 |
| 1.3 | DB migration：`points_ledger`、`coupon_inventory`、`member_balance` |
| 1.4 | 全量导入 Service：调有赞 API 拉积分/优惠券/会员卡，幂等写入 |
| 1.5 | Webhook 增量写入（POINTS→ledger, COUPON→inventory 反查补全） |
| 1.6 | 本地全量验证 + 生产执行 + LOGBOOK 收口 |

### M2：储值余额（4 天）

模型/仓储/充值Service/小程序API/储值支付+组合支付

### M3：积分模块（规则已确认，暂估 4–5 天）

**业务规则（已确认）**

- 获得：`1 元实付 = 1 分`；实付现金 = `total_fen - balance_fen - points_fen`；不足 1 元向下取整，`award_points = cash_fen // 100`。
- 抵扣：`100 分 = 1 元`；单笔最低 `100 分`；最高抵扣 `50% × total_fen`，且 `points_fen <= total_fen - balance_fen`；可用积分按百位向下取整，`points_used = floor(available / 100) × 100`。
- 发放时点：支付成功即发分；`apply-points` 只写快照，支付成功时才真正扣减抵扣积分。
- 叠加：`remain_fen = total_fen - balance_fen - points_fen`。
- 有效期：长期有效。
- 退款：当前系统无部分退款；全单退款退回全部 `pointsUsed`、收回全部 `pointsAwarded`。
- 数据主从：配置开关 `points_authority`（默认 `youzan`）两步切换——M3 上线保持 `youzan`（有赞 `total` 继续维护余额），验证稳定后改 `local` 再部署，切为本地 `member_balance.points` 权威；`local` 下有赞 `POINTS` 事件只写流水/审计，不再覆盖余额。

**M3.1 数据/仓储**

- `v023`：`points_ledger.source` 扩为 `webhook/import/order`；新增 `biz_type`（`order_award/order_redeem/order_refund`）、`biz_id`；`total` 继续表示变动后余额，不新增 `balance_after`。
- `member_balance_repo`：新增 `get_points/credit_points/deduct_points_if_sufficient`（原子条件更新，参照储值同款）。
- `points_ledger_repo`：新增 `list_by_mobile`；`get_by_unique_id` 复用。
- `points_ledger` 模型：`PointsLedgerEntry` 增 `biz_type/biz_id`，`LedgerSource` 增 `ORDER = "order"`。
- `event_member._handle_points_event`：`points_authority=local` 时不再把有赞 `total` 写进 `member_balance.points`，只写 `points_ledger` 作为审计镜像；`youzan` 模式保持现状。

**M3.2 积分 Service**

- `app/service/points/rules.py`：纯函数 `award_points(cash_fen)`、`redeem_units(available, total_fen, balance_fen)`、`refund_reversal`。
- `app/service/points/ledger.py`：credit/deduct + 写流水；幂等键 `points:award:<order_id>`、`points:redeem:<order_id>`、`points:refund:<order_id>`。
- `app/service/points/payment.py`：`apply_points_snapshot`、`award_on_payment`、`refund_points`。
- `__init__.py` 门面 `PointsService`：`get_points/get_ledger/redeem_preview/apply_points/award_on_payment/refund_points`。

**M3.3 支付联动**

- `payment.json` 新增 `pointsFen/pointsUsed/pointsAwarded`。
- `apply-points` 必须把订单写为 `partial`，生成 `pointsFen/pointsUsed/remainFen`，后续微信/mock 按 `remainFen` 收款，不能只放快照。
- `build_combined_payment`、`prepare-payment`、微信通知金额校验统一支持 `pointsFen`：`remain_fen = total_fen - balance_fen - points_fen`。
- 三条支付成功路径（mock、微信通知、储值全额支付）统一调 `award_on_payment`，重复通知幂等。
- 取消/超时/后台取消按支付快照调 `refund_points`。

**M3.4 小程序 API**

- `GET /api/v1/miniapp/points`：余额 + 明细。
- `POST /api/v1/miniapp/orders/{order_id}/points-preview`：试算不落账。
- `POST /api/v1/miniapp/orders/{order_id}/apply-points`：校验并写 partial 快照。
- 新增 `app/api/channels/storefront/points.py`，鉴权沿用 `authenticate_storefront_request` 并在 storefront 装配点注册。

**M3.5 验证/收口**

- 规则纯函数单测、仓储幂等/余额不足单测、三路径发分一次、重复通知幂等、组合金额正确、取消退积分。
- 全套测试 + `ruff` + `check_file_sizes` + `check_project --skip-tests`。
- 本地验证 → 生产部署 → LOGBOOK/项目进度清单收口，按 M1/M2 模式。

> 说明：小程序页面仍归 M5，M3 只交付 API 与账务闭环。

### M4：优惠券模块（4 天）

模型/仓储/管理后台/核销引擎/小程序API

### M5：小程序前端（3 天）

我的页真实API/充值页/积分明细/优惠券中心/结算页扩展

### M6：收口部署（1 天）

---

## 架构约束

- 禁止 `api/` → `repository/` 直调
- 禁止 SQL f-string、`Optional[X]`、`SELECT *`
- 原子条件更新（同订单支付一致性模式）
- POINTS 用 `unique_id` 去重，COUPON 用 `id`+`status`+`mobile` 组合去重
- mock 支付显式开关

---

## M1 执行记录（2026-08-12）

- 1.1 ✅ `event_member.py`：四类事件解析与分发
- 1.2 ✅ `event_handler.py` 新增会员事件路由分支；webhook 审计归类 MEMBER
- 1.3 ✅ v021 迁移：`points_ledger` / `coupon_inventory` / `member_balance`（本地库已应用，schema_version=21）
- 1.4 ✅ 全量导入 Service + `scripts/import_member_loyalty.py`（dry-run/apply/limit/JSON）
- 1.5 ✅ Webhook 增量写入（POINTS→ledger，COUPON→inventory 反查补全）
- 1.6 ✅ 本地验证 + 生产执行完成：部署 v0.111.0（ecffa3b），v021 三表落库（schema_version=21）、/ready database_schema_ready=true、Webhook 会员路由生效；生产全量导入待真实店铺 API 契约验证后执行

### M1 关键决策
### M2 执行记录（2026-08-12）

- 模型/仓储 ✅ v022 迁移新增 `stored_value_recharge`（unpaid/paid/cancelled/expired）+ `balance_ledger`（unique_id 幂等、amount_fen 带符号）；`app/models/stored_value.py`、`app/constants/stored_value.py`（单笔 100~50000 分）
- 充值 Service ✅ `app/service/stored_value/recharge.py`：创建/取消/mock 确认幂等入账（`recharge:<id>` 幂等键）/列表；`member.py` 身份解析（openid→identity_links→primary_phone）+ credit/deduct 原子记账
- 储值支付+组合支付 ✅ `app/service/stored_value/payment.py`：全额余额支付防超扣（原子扣款+条件更新）；组合支付先扣余额置 partial（balanceFen/remainFen）再返回差额 mock/微信会话；取消/超时/后台取消按 `payment.balanceFen` 原路退款（`order_refund:<order_id>` 幂等）
- 小程序 API ✅ `recharges.py`（充值/余额端点）+ `orders.py`（pay-with-balance / prepare-combined-payment）；既有 `POST /{order_id}/mock-pay` 支持从 partial 完成支付
- 边界修复 ✅ 消除 `stored_value ↔ order` 循环导入（TYPE_CHECKING + `from __future__ import annotations`）；组合支付差额走微信时按 `remainFen` 校验通知金额；余额全额支付订单不可取消/不退款
- 验证 ✅ 储值域 14 项测试全过；全套 1365 项通过（含 tests/scripts），覆盖率 82.54%；ruff / check_file_sizes / check_project --skip-tests 全绿；本地库 v022 已应用（schema_version=22）
- 待办 ⏳ 真实微信支付（商户号到位后）：组合支付差额走微信 JSAPI、支付通知与余额原路退款；M5 小程序前端（充值页/余额明细/结算页组合支付入口）


- POINTS 去重键 `unique_id`；COUPON 去重键 `id+status+mobile`（状态流转写多行，符合生命周期记录语义）
- `member_balance.upsert_identity` 采用「None 不更新、显式 0 覆盖」，防止卡片/身份事件抹掉积分余额
- 会员域 API 名称以常量集中管理（`app/service/youzan/member_api.py`），真实店铺联调前需按实际开通权限验证
- 全量导入只落余额快照与券库存，积分明细流水由 Webhook 增量维护，避免导入快照污染明细
