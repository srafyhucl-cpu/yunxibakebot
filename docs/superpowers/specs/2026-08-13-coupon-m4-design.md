# M4 优惠券模块设计

- 状态：待批准
- trace_id：`20260813-coupon-m4`
- 来源：计划书 `docs/specs/2026-08-12-member-loyalty-storedvalue-plan.md`（M4 优惠券模块）；brainstorming 与用户确认（7 项决策）
- 前置：M1 数据底座（`coupon_inventory` 生命周期记录 + 全量导入 + COUPON 事件增量）、M2 储值闭环、M3 积分闭环

## 目标

在 M1 优惠券库存底座之上，交付优惠券模块闭环：券模板统一建模、本地核销引擎（订单结算抵扣）、支付/退款联动、小程序券 API、管理后台模板管理与查询。数据主从 `COUPON_AUTHORITY` 默认 `youzan`（有赞发券，本地镜像 + 本地核销），预留 `local` 模式与后续运营能力（定向发券、数据看板）演进。

## 范围与边界

**范围内**
- 券类型：满减券（满 X 减 Y）、无门槛代金券、折扣券（含优惠上限）。
- 结算抵扣核销：选券 → 写支付快照 → 支付成功核销（TAKE→CONSUME）→ 退款/取消退回（BACK/TAKE）。
- 抵扣叠加：`remain_fen = total_fen - coupon_fen - balance_fen - points_fen`。
- 小程序 API：我的券列表、结算选券预览、应用券。
- 管理后台：券模板 CRUD/启停、发券记录/核销记录/库存查询、local 模式发券。
- 数据主从开关 `COUPON_AUTHORITY`（youzan/local），与 `POINTS_AUTHORITY` 同构。

**范围外（本期不做）**
- 商家扫码/到店核销（用户已确认无此场景）。
- 商品维度可用性校验：券模板保留适用商品/分类字段（`scope_json`），有赞同步时填充，但 M4 结算校验只做金额维度。
- 定向发券、数据看板（向 C 演进，本期只预留字段与扩展位）。
- 部分退款（沿用全单退款语义，与 M3 一致）。

## 业务规则

### 券类型与抵扣计算（`rules.py` 纯函数）

| 类型 | 可用条件 | 抵扣金额 |
|---|---|---|
| FULL_REDUCTION 满减 | `total_fen >= threshold_fen` | `min(value_fen, total_fen)` |
| NO_THRESHOLD 无门槛 | 无门槛 | `min(value_fen, total_fen)` |
| DISCOUNT 折扣 | 无门槛 | `min(total_fen * (10000 - discount_bp) // 10000, cap_fen or 无穷, total_fen)`，至少 1 分 |

- 券自身有效期（`valid_from/valid_until`）内且状态 `TAKE` 才可用；过期券不参与可用列表。
- 抵扣不能超过订单应付，且与储值、积分叠加后 `remain_fen >= 0`。

### 叠加约束（与 M3 积分规则协调）

- 选券（apply-coupon）与选积分（apply-points）顺序不敏感，最终支付快照统一校验：
  - `coupon_fen + balance_fen + points_fen <= total_fen`
  - 积分抵扣保持 M3 规则：`points_fen <= 50% * total_fen`，且 `points_fen <= total_fen - coupon_fen - balance_fen`（券先抵扣后积分上限相应收窄）。
- 取消/超时/后台取消：按快照退回券（`CONSUME -> BACK`，未过期可恢复可用）与积分（M3 既有逻辑）。

### 幂等与并发

- 券核销原子条件更新：`UPDATE coupon_inventory SET status='CONSUME', ... WHERE id=? AND status='TAKE'`，影响行数为 1 才算成功；并发/重复支付只有一个能核销。
- 幂等键：`coupon:consume:<order_id>`、`coupon:refund:<order_id>`（与积分 `points:*` 幂等键同构）。
- 去重键沿用 M1：`coupon_id + status + mobile` 组合去重（生命周期记录语义）。

### 数据主从

- `COUPON_AUTHORITY` 默认 `youzan`：有赞发券，本地镜像券生命周期 + 本地核销引擎为准；有赞 `COUPON_CUSTOMER_PROMOTION` 事件增量校准（`TAKE/CONSUME/BACK` 写镜像）；调有赞核销 API 封装为可选调用、默认 mock 短路（真实店铺 API 契约验证后再启用，沿用 M1 待办）。
- `local` 模式：有赞券事件只写审计（类似 `POINTS_AUTHORITY=local`），本地 `coupon_grants` 发券 + 本地核销引擎权威；有赞停用后由后台在本地定义模板并发券。

## 数据模型（v024 迁移）

### 新增 `coupon_templates`（券模板）

| 字段 | 说明 |
|---|---|
| `id` | 主键（youzan 用 coupon_group_id，local 用 uuid） |
| `name` | 券名称 |
| `coupon_type` | FULL_REDUCTION / NO_THRESHOLD / DISCOUNT |
| `threshold_fen` | 满减门槛（无门槛=0） |
| `value_fen` | 面额（折扣券=0） |
| `discount_bp` | 折扣万分比（如 9000=9 折；非折扣券=0） |
| `cap_fen` | 折扣优惠上限（0=不限） |
| `valid_from` / `valid_until` | 模板有效期 |
| `scope_json` | 适用商品/分类（预留，默认 `{}` 全场，暂不参与结算校验） |
| `status` | active / disabled |
| `source` | youzan / local |
| `created_at` / `updated_at` | 时间戳 |

### 扩展 `coupon_inventory`（券实例生命周期）

新增列：`template_id`、`valid_from`、`valid_until`、`deducted_fen`（核销抵扣金额）、`consumed_at`、`refunded_at`。状态沿用 `TAKE / CONSUME / BACK`（`BACK` 表示退回；过期由有效期判断，不单独落状态）。

### 新增 `coupon_grants`（发券记录，local 模式）

| 字段 | 说明 |
|---|---|
| `id` | 主键 |
| `template_id` | 关联模板 |
| `customer_id` / `mobile` | 领券人 |
| `coupon_code` | 券码（local 发券生成） |
| `granted_by` | 操作人（admin 账号或 system） |
| `channel` | 发券渠道（预留：admin/batch/auto） |
| `audience_json` | 人群/标签（预留 C 定向发券） |
| `status` | granted / revoked |
| `created_at` | 时间戳 |

## 分层设计

```
api/ → service/coupon/ → repository/ → models/
```

- `app/models/member.py` 或新建 `app/models/coupon.py`：`CouponTemplate`、`CouponGrant`、扩展 `CouponInventoryEntry`。
- `app/repository/coupon_template_repo.py`：模板 CRUD、`list_active`、`get_by_type`。
- `app/repository/coupon_inventory_repo.py` 扩展：`list_by_mobile`（含状态/有效期筛选）、`get_available`、`consume`（原子条件更新）、`refund`、`list_by_order`。
- `app/repository/coupon_grant_repo.py`：`insert`、`list_by_mobile`、`revoke`。
- `app/service/coupon/rules.py`：纯函数（可用性、抵扣计算、叠加校验）。
- `app/service/coupon/inventory.py`：券账本（核销/退回，幂等键）。
- `app/service/coupon/payment.py`：`build_coupon_payment` 快照、`consume_on_payment`、`refund_coupon`。
- `app/service/coupon/grants.py`：local 发券/回收。
- `app/service/coupon/__init__.py`：`CouponService` 门面（`get_my_coupons` / `redeem_preview` / `apply_coupon`）。

## 支付联动（与 M3 积分闭环同构）

- `build_coupon_payment`：结算选券写支付快照（`couponFen/couponId`），订单进入 partial 中间态。
- 三条支付成功路径（mock、微信通知、储值全额）统一调 `consume_on_payment`：按快照原子核销券；非会员/无券订单自动跳过。
- 取消/超时/后台取消调 `refund_coupon`：按快照退回券（幂等键防重）。
- 有赞核销 API 调用封装在 `member_api.py`（mock 短路），真实契约验证后启用。

## 小程序 API（3 端点，prefix `/api/v1/miniapp`）

| 端点 | 说明 |
|---|---|
| `GET /coupons` | 我的券列表（按状态/有效期筛选） |
| `POST /orders/{order_id}/coupon-preview` | 结算选券预览（可用券 + 每张可减金额 + 叠加校验结果） |
| `POST /orders/{order_id}/apply-coupon` | 应用券（写快照，支付成功才核销） |

鉴权沿用 `authenticate_storefront_request` + `x-miniapp-user-id`，错误语义与积分 API 一致（ValueError → 400）。

## 管理后台

- `app/api/admin/coupons.py`：
  - 券模板：列表 / 新建 / 编辑 / 启停（`coupon_authority=local` 时后台创建模板并发券）。
  - 查询：发券记录、核销记录、券库存明细（按状态/模板/手机号筛选）。
  - `local` 发券：按手机号发放指定模板券，生成 `coupon_code` 写 `coupon_grants` 并落 `coupon_inventory`。
- `web/admin/src/pages/coupons/`：`CouponsPage.vue`（模板管理 + 记录查询 + local 发券入口），沿用现有 admin 页面模式（API service + Element Plus）。

## 演进预留（向 C 转）

- 模板表已含 `scope_json`、渠道/人群字段（`coupon_grants.channel/audience_json`），定向发券可直接扩展发券表单与 API 参数。
- 核销记录含 `deducted_fen/consumed_at/order_no`，数据看板可直接聚合（领券数/核销数/核销率/优惠金额）。

## 测试验收

1. `rules.py`：三类券可用性（门槛/有效期/上限）与抵扣金额边界（含超应付、折扣取整、上限封顶）。
2. 叠加约束：券+储值+积分不超应付；积分 50% 上限在叠加券后正确收窄。
3. 幂等与并发：重复支付/重复取消只核销/退回一次；`TAKE->CONSUME` 原子条件更新并发只有一个成功。
4. 支付联动：mock/微信/储值三条成功路径核销券；取消/超时/后台取消退回券；非会员无券订单跳过。
5. 小程序 API：列表/预览/应用三端点鉴权与错误语义；lifespan 装配契约测试同步更新。
6. 管理后台：模板 CRUD/启停、发券记录、核销记录、local 发券。
7. 全套回归：新增测试 + `tests/` 全套 + `check_project --skip-tests` + `check_file_sizes` + `ruff check` + `ruff format --check` + 门禁全绿。

## 收口

- 本地验证全绿后按 M6 模式生产部署：先 `COUPON_AUTHORITY=youzan` 部署观察，稳定后（如需）切 `local`。
- LOGBOOK / 项目进度清单 / 执行计划（writing-plans）收口，证据归档按 harness 规范。
