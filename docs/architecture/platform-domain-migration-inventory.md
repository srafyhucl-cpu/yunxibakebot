# Platform 领域迁移盘点

本文件记录 `Platform` 仓内部从历史 `miniapp_*` 命名继续收口到 canonical 领域的当前盘点结果。它不是新的接口契约；外部路径仍以 `docs/architecture/platform-miniapp-api-contract-v1.md` 为准。

## 结论

- `app/service/miniapp_*.py` 当前已经基本退化为兼容 facade，只做旧类名、常量或函数名导出。
- 真实服务实现已主要落在 `customer / order / catalog / conversation / channels/storefront / integrations / ops`。
- 下一阶段不应优先改 HTTP 路径、数据库表名或 MiniApp API 契约，而应先减少内部测试、仓储和模型对 `miniapp_*` 兼容命名的依赖。
- 风险最高的遗留点是地址域：`miniapp_addresses`、`miniapp_address_audit` 仍是数据库表名，`MiniappAddressRepo` / `MiniappAddress` 仍是仓储和模型名，但其业务归属已经是 `customer`。

## 当前分层现状

| 历史入口 | 当前 canonical 归属 | 现状判断 | 下一步 |
|---|---|---|---|
| `app/service/miniapp_auth.py` | `channels/storefront` | 纯 facade，导出 `StorefrontAuthService as MiniappAuthService` | 暂保留，禁止新代码依赖 |
| `app/service/miniapp_catalog.py` | `catalog` | 纯 facade，导出 `CatalogApplicationService` | 暂保留，测试逐步改用 `catalog` |
| `app/service/miniapp_order.py` | `order` | 纯 facade，导出 `OrderApplicationService` | 暂保留，测试逐步改用 `order` |
| `app/service/miniapp_payment.py` | `order` + `integrations` | facade，但仍集中导出较多支付常量 | 先把测试改到 `order.payment_state` / `order.payment_runtime` |
| `app/service/miniapp_address.py` | `customer` | 纯 facade，导出 `CustomerAddressService` | 暂保留，地址仓储和模型另行迁移 |
| `app/service/miniapp_chat.py` | `conversation` + `channels/storefront` | facade，保留 `MINIAPP_CHAT_CHANNEL` 兼容常量 | 暂保留，测试逐步改用 `StorefrontConversationService` |
| `app/service/miniapp_order_inventory.py` | `order` | 纯 facade | 测试改用 `app.service.order.inventory` |
| `app/service/miniapp_order_schedule.py` | `order` | 纯 facade | 测试改用 `app.service.order.schedule` |
| `app/service/miniapp_order_serialization.py` | `order` | 纯 facade | 测试改用 `app.service.order.serialization` |
| `app/service/miniapp_order_timeout.py` | `ops` | 纯 facade | 测试改用 `app.service.ops.order_timeout_scheduler` |

## 仍需收口的遗留点

### P0：保持稳定，不在下一步改

- `/api/v1/miniapp/*` HTTP 路径。
- `x-miniapp-user-id` 请求头。
- `miniapp_addresses`、`miniapp_address_audit` 数据库表名。
- 历史迁移文件名，例如 `v008_miniapp_addresses.sql`。
- `YunxiBakeBot` / `YunxiBakeMiniApp` 仓库路径名。

这些名字承担兼容契约或历史迁移语义，贸然改动会增加联调、数据迁移和回滚风险。

### P1：可以优先做的低风险收口

- 将 app 内部新增代码统一依赖 canonical 服务，继续保持 `scripts/check_project.py` 的红线：`app` 内禁止导入 `app.service.miniapp_*`。
- 把现有测试里对 `MiniappPaymentService`、`MiniappOrderInventoryService`、`MiniappAddressRepo` 等兼容名的依赖，逐步替换为 canonical 名称。
- 在测试替换完成后，保留 facade 文件作为外部兼容入口，但不再把它们当作主要测试目标。
- 对 `lifespan_services.py` 中的旧 service key 保持兼容别名，同时新增测试确保路由优先使用 canonical key。

### P2：需要设计后再做的中风险收口

- 为地址域增加 canonical repo/model 别名，例如 `CustomerAddressRepo`、`CustomerAddress`，先映射到既有表和既有字段。
- 让 `app/service/customer/address.py`、`address_admin.py` 依赖 customer 命名的 repo/model 别名。
- 继续保留 `MiniappAddressRepo`、`MiniappAddress` 作为兼容导出，避免一次性冲击测试和历史调用。
- 等客户主档和企微绑定路径稳定后，再评估是否需要新增真正的 `customer_addresses` 表；现阶段不建议做表重命名。

### P3：后续产品化再评估

- 是否把 `/api/v1/miniapp/*` 对外路径另起 `/api/v1/storefront/*`。
- 是否改仓库 slug。
- 是否把 `x-miniapp-user-id` 升级为通用渠道身份头。
- 是否将前台渠道从微信小程序扩展到 H5、抖音、小红书或其他入口。

这些属于渠道产品化阶段，不应混入当前内部领域治理。

## 建议执行批次

1. **测试依赖迁移批次**
   - 修改服务层测试，让它们直接导入 `app.service.order.*`、`app.service.customer.*`、`app.service.catalog.*`、`app.service.conversation.*`。
   - 保留 API 测试文件名中的 `miniapp`，因为它们验证的是外部兼容路径。

2. **地址域别名批次**
   - 新增 customer 语义的 repo/model 别名。
   - 调整 customer address service 依赖 canonical 名称。
   - 保持数据库表、迁移和旧 repo/model 导出不变。

3. **service facade 降噪批次**
   - 检查 `app/service/miniapp_*.py` 是否只剩导出。
   - 如果某个 facade 已无内部测试和内部调用，仅保留最小兼容导出和中文说明。

4. **文档与红线同步批次**
   - 更新 `project-boundaries.md` 的现状收口段落。
   - 将新增红线或兼容期约束补到 `docs/AGENTS/quick-reference.md` 或 `scripts/check_project.py`。

## 验证要求

- 架构红线：
  - `rg "from app\.repository" app/api --include="*.py"` 必须零输出。
  - `rg "import aiosqlite|\.execute\(|\.fetchone\(|\.fetchall\(" app/service --include="*.py"` 必须零输出或只剩已知合规封装。
  - `rg "from app\.(service|repository|api)" app/models --include="*.py"` 必须零输出。
  - `python scripts/check_project.py` 必须通过。
- 回归测试：
  - 地址：`tests/api/test_miniapp_address_api.py`、`tests/api/test_admin_address_api.py`、`tests/service/test_miniapp_address.py`。
  - 订单与支付：`tests/service/test_miniapp_order.py`、`tests/api/test_miniapp_order_api.py`、`tests/api/test_miniapp_payment_api.py`。
  - 路由装配：`tests/test_lifespan_routes_services.py`。

## 当前判断

`Platform` 的服务层已经完成了第一轮真实收口，下一步的价值不在继续抽象命名，而在把测试和内部依赖慢慢迁到 canonical 名称。地址域是最值得优先处理的残留点，但应采用 repo/model 别名过渡，不碰数据库表名。
