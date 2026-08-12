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

### M3：积分模块（3 天）

模型/仓储/规则引擎/支付联动发积分/积分抵扣/退款退回/小程序API

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
- 1.6 ⏳ 本地验证完成（7 项新测试 + 1348 全量 + 门禁全绿）；生产执行待真实店铺 API 契约验证与用户确认部署窗口

### M1 关键决策

- POINTS 去重键 `unique_id`；COUPON 去重键 `id+status+mobile`（状态流转写多行，符合生命周期记录语义）
- `member_balance.upsert_identity` 采用「None 不更新、显式 0 覆盖」，防止卡片/身份事件抹掉积分余额
- 会员域 API 名称以常量集中管理（`app/service/youzan/member_api.py`），真实店铺联调前需按实际开通权限验证
- 全量导入只落余额快照与券库存，积分明细流水由 Webhook 增量维护，避免导入快照污染明细
