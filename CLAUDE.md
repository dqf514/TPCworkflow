# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

IMC Workflow —— 企业级工作流/审批平台，主场景是费用报销。后端 Flask + SQLAlchemy + SQLite，前端 Vue 3 + Vite，另有一个 WPF 桌面客户端（WebView2 壳）复用同一套前端。

三个可独立部署的部分：

| 目录 | 技术栈 | 说明 |
|------|--------|------|
| `backend/` | Flask 3 + SQLAlchemy + SQLite | API + 业务逻辑 + 数据库，端口 **5320** |
| `frontend/` | Vue 3 + TS + Vite 6 + Arco Design + Tailwind | SPA，端口 **5321**，构建产物 `frontend/dist` 由 Flask 直接托管 |
| `client/` | C# / WPF / net10.0-windows | Windows 桌面客户端，仅嵌 WebView2 打开同一前端 |

`deploy/` 存放 nginx 配置与客户端安装包。根目录的 `README.md` 已过时（端口、依赖说明与当前代码不符），以本文件为准。

## 常用命令

### 后端

```bash
cd backend
./.venv/Scripts/Activate.ps1          # Windows PowerShell
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
copy .env.example .env                # .env 会被自动加载（config.py 里的 load_dotenv）
python run.py                         # http://127.0.0.1:5320
```

`.env` 里的 `SECRET_KEY` 必须是随机长字符串；留空或写示例值时，非调试模式（`FLASK_DEBUG=0`）会自动生成并持久化到 `backend/data/.secret_key`，调试模式才允许用公开默认值。

升级数据库（**唯一的 schema 迁移途径**，见下文）：

```bash
python scripts/upgrade_db.py          # create_all → _ensure_columns → 约束迁移 → bootstrap → i18n 种子
```

### 前端

```bash
cd frontend
npm install --registry=https://registry.npmmirror.com
npm run dev                           # http://127.0.0.1:5321，/api 代理到 :5320
npm run build                         # 产物 frontend/dist
```

`dev`/`build` 都会先跑 `npm run copy-pdfjs`，把 pdfjs 的 `cmaps`/`standard_fonts` 拷到 `public/pdfjs/`（中文 PDF 渲染必需）。

前端**没有** lint / test / typecheck 脚本；`vue-tsc` 装了但没接进任何命令，验证只能靠 `npm run build`。

### 客户端

```bash
cd client
dotnet build -c Release
./publish.ps1                         # 单文件自包含发布 → deploy/downloads/
```

### 测试

后端没有 pytest 套件，测试是 `backend/scripts/test_*.py` 里的**独立可运行脚本**（`assert` + 真实 SQLite 库），直接执行：

```bash
cd backend
python scripts/test_workflow_conditions.py     # 条件分支与流程引擎
python scripts/test_add_sign.py                # 前/后加签、驳回、或签
python scripts/test_receipt_duplicate.py       # 票据重复使用校验
python scripts/test_instance_uuid.py           # 实例 public uuid 访问控制
python scripts/test_dept_manager_resolve.py    # 部门经理解析与跳过策略
python scripts/test_workflow_fixes.py          # 会签人数口径 + 驳回作废同伴待办（用独立临时库）
python scripts/e2e_smoke.py                   # 表单→发布→发起→审批→结束 全链路
```

`test_approval_email.py` 需要真实 SMTP。

> `scripts/test_*.py` 大多直接跑在开发库 `data/tpcworkflow.db` 上，会留下测试数据；新写的测试请像 `test_workflow_fixes.py` 那样用 `DATABASE_URI` 指向临时库。

## 架构

### 后端

```
backend/app/
  __init__.py      create_app() 工厂：ProxyFix → db/login_manager → 注册 20 个蓝图 → SPA 兜底路由
  extensions.py    db = SQLAlchemy(), login_manager = LoginManager()
  startup.py       ensure_db_tables / run_startup_maintenance（受 TPC_RUN_STARTUP_MAINTENANCE 控制）
  api/             19 个蓝图模块，一个领域一个文件
  models/          16 个模型模块，43 张表，显式 __tablename__
  services/        60+ 个业务服务模块（真正的业务逻辑在这里）
  utils/           response.py（响应信封）、client_auth.py、locale.py 等
```

**认证没有 JWT。** 三种方式并存：
- Web：Flask-Login session cookie（`login_manager.user_loader` → `User`）。
- 桌面客户端：`Authorization: Bearer <device token>`，24h access / 90d refresh，见 `app/services/device_auth.py`，hash 存 `user_devices`。全局 `before_request` 会把 Bearer 自动提升为 session。
- 邮件快捷审批：`/api/v1/workflow/tasks/email-action` 用一次性 token（`TaskEmailToken`），**故意不走 session**，返回渲染好的 HTML。

**响应信封**统一由 `app/utils/response.py` 的 `ok()/fail()` 生成：

```json
{"ok": true, "data": ..., "message": "操作成功"}
{"ok": false, "message": "...", "code": "...", "data": ...}
```

前端 `src/api/client.ts` 的 `ApiResponse<T>` 就是这个形状。唯一例外是 `GET /api/v1/health`。

**RBAC 分三层，且全部是内联判断，没有装饰器**：

1. 全局管理员：`User.is_system_admin`（`app/api/admin.py` 的 `_require_admin`）。
2. 分级（sector）管理员：`UserScopedAdmin` 存 `sector_ids` + `can_design_workflow` / `can_view_instances` / `can_export_instances` 三个能力位，统一入口是 `app/services/permissions.py`（`admin_capabilities(user)` 返回给前端）。路由里逐个调用 `user_can_access_sector()` 等。
3. 流程角色：`FlowRole` / `FlowRoleMember` —— **审批角色，与管理角色严格分离**（财务、法务、部门负责人等）。见 `app/services/flow_role_service.py`。

前端路由守卫 `frontend/src/router/index.ts` 里有对应的降级：`meta.admin` 页面可按 `formStudio` / `sectorMonitor` / `financeExport` 这些 meta 标记放行给分级管理员。

**SPA 托管**：Flask 用 `@app.route('/<path:path>')` 兜底，从 `frontend/dist` 取真实文件，否则回 `index.html`；`api/` 前缀返回 JSON 404。所以 **改完前端必须 `npm run build`**，后端才会提供新页面。

### 数据库与迁移

Flask-SQLAlchemy + SQLite（`backend/data/tpcworkflow.db`）。**Alembic 已配置但从未使用** —— `backend/migrations/` 里没有 `versions/` 目录，没有任何 revision。

真正的迁移是手写的 `backend/scripts/upgrade_db.py`：
- `_ensure_columns()` 用 `ALTER TABLE ... ADD COLUMN` 补齐历次新增的列（并含若干数据回填）。
- `_migrate_department_unique_constraint()` 等处理部门表唯一约束变更（SQLite 需整表重建）。

**新增/改动字段时必须同步更新 `upgrade_db.py`**，否则老库不会自动得到该列。

启动性能是刻意优化的：`create_app` 发现表已存在就跳过 `create_all`，迁移与种子默认**不跑**。所以代码升级后要手动执行 `python scripts/upgrade_db.py`。开发时设 `FLASK_DEBUG=1` 或 `TPC_RUN_STARTUP_MAINTENANCE=1` 可让启动顺带维护。

`backend/scripts/bootstrap.py` 的 `ensure_bootstrap()` 是幂等种子：默认账号 `admin`/`admin123`、示例公司与「示例请假」流程、business sector、汇率、内置已发布模板等。`upgrade_db.py` 的 `upgrade_all()` 会调用它。

### 工作流引擎（核心）

主文件 `backend/app/services/workflow_engine.py`，类 `WorkflowEngine`。流程图 JSON 存在 `WorkflowDefinition.process_graph`（Text 字段，JSON 序列化）。

节点 `type`：`start` | `approver` | `handler` | `cc` | `condition` | `parallel` | `end`。

| 关注点 | 文件 | 要点 |
|--------|------|------|
| 实例创建/发起 | `workflow_engine.py:start` | 解析图 → 找 start 节点 → 播种 `variables['org']` → 建 `WorkflowInstance` → 分配 `display_no` → `_advance` |
| 节点执行 | `workflow_engine.py:_advance` | **按 node type 分派的核心方法，新增节点类型就改这里** |
| 审批完成 | `workflow_engine.py:complete_task` | 校验 → 加签分支 → 合并 `form_update` → 节点字段必填校验 → 意见/签名校验 → 转交/加签 → 写 timeline → `_continue_after_task_approved` |
| 或签/会签/依次判定 | `workflow_engine.py:_node_approved` | `apv_rel` = `or` / `and` / `sequential`；`and` 需比较已通过数 vs 解析出的审批人数 |
| 条件表达式求值 | `graph_utils.py:eval_condition` | dict 形式 `{field, op, value}`，op 支持 `eq/ne/gt/gte/lt/lte`；另支持 `'default'` |
| 分支解析 | `graph_utils.py:resolve_next_node_ids` | 按 `priority` 排序取第一个命中分支 |
| 审批人解析 | `assignee_resolver.py:AssigneeResolver` | `assignee_type`：`fixed_users` / `initiator` / `flow_role` / `dept_manager` / `initiator_dept_manager` / `parent_dept_manager` / `dept_chain` |
| 部门经理跳过策略 | `assignee_resolver.py:apply_dept_manager_skip_policy` | 无经理→跳过；唯一经理是发起人→跳过；否则剔除发起人避免自审 |
| 审批人过滤与自动通过 | `workflow_task_utils.py` | `resolve_assignees_for_node` 返回 `(assignees, auto_skip, reason)`；同一表单重复审批人可自动通过 |
| 加签 | `workflow_add_sign.py` | 前加签（before）/ 后加签（after），兄弟节点全部完成后才释放父节点 |
| 依次审批队列 | `workflow_engine.py:_spawn_next_sequential_task` / `_try_sequential_continue` | 队列存于 `action_meta.sequential_queue` |
| 审批设置开关 | `workflow_settings.py:DEFAULT_WORKFLOW_SETTINGS` | `require_comment` / `require_handwritten_sign` / `require_handler_comment` / `allow_add_sign` / `allow_transfer` 等，由 `merge_settings(raw)` 合并 |
| 节点字段必填 | `node_field_requirements.py` | 逐节点的「必须填写 / 必须修改」校验 |
| 时间线 | `workflow_engine.py:_append_timeline` | `InstanceTimeline` 只追加，是审批轨迹的唯一真相 |
| 实例可见性 | `apply_visibility.py` / `instance_access.py` | 谁能发起、谁能查看（按是否参与过 + public uuid） |
| 实例单号 | `instance_number.py` | `YYYY-MM-DD-0001`，按自然日递增 |

表单 schema 与流程图**一起**存在 `FormDefinition` 上（`form_schema` + `process_graph` + `workflow_settings`），前端设计器保存的就是这三块（见 `frontend/src/views/admin/FormStudioView.vue`）。

### 后端其他领域（`app/services/`）

- **表单**：`form_schema.py`（字段类型注册表、`validate_form_data`、`flatten_fields`）、`form_visibility.py`（联动/条件显示）、`form_serial_no.py`（流水号）、`date_range_value.py`（日期区间 0.5 天精度）、`record_set_service.py`（公司级选项集 vs 个人记录集）。
- **财务**：`finance_export_profiles.py`（用友 YonSuite BIP 凭证导入档案）、`finance_voucher_export.py`（填充 `backend/templates/finance/yonsuite_voucher_import.xlsx` 生成凭证）、`finance_export_mapping_service.py`（按 sector 的列↔字段映射）、`receipt_duplicate_service.py`（票据重复使用检测）、`exchange_rate`（多币种）。
- **AI**：`llm_client.py`（base-url 规范化、`@internal:port` → 本地）、`llm_chat.py`（OpenAI 兼容 / **Anthropic** / Ollama 三种 provider，带 fallback 与 `extract_json_object`）、`receipt_recognition_service.py`（PDF→图像→识别→回填建议，用 PyMuPDF）。**所有 LLM HTTP 调用用 `urllib.request`，项目没有装 `requests`。**
- **通知**：`notify.py`（SMTP 配置来自 DB+env、登录验证码、待办通知、节点额外收件人）、`email_content.py`（审批邮件的中文字段摘要）、`email_action_page.py`（邮件一键审批页）、`document_delivery.py`（审批通过后给客户的独立 SMTP）。
- **国际化**：`i18n.py`（`t(namespace.key, locale, **kwargs)`、bundle 版本）、`i18n_catalog.py`（后台字典目录）。字典存库，**改文案不用重新编译前端**。
- **其他**：`holiday_calendar.py`（chinesecalendar + holidays）、`audit_log_service.py`（认证事件、页面浏览、API 访问日志，`after_request` 挂钩）、`print_template_service.py`、`client_events.py`（SSE 事件总线）。

### 前端

```
frontend/src/
  main.ts               启动：initTheme → embed 检测 → await loadLocaleMessages → 挂载 pinia/router/i18n/Arco
  router/index.ts       全部路由 + 登录/权限守卫（meta.admin + meta.public）
  api/client.ts         唯一的 API 模块，axios baseURL='/api/v1'，withCredentials
  stores/               auth.ts（用户 + 所有权限位）、branding.ts、workflowBadges.ts
  layouts/AppLayout.vue 应用外壳：顶栏 + 侧边栏 + 移动端 TabBar + 命令面板 + 个人资料弹窗
  views/                用户页（Login/Dashboard/ApplyCatalog/ApplyFlow/Tasks/TaskDetail/MyInstances/InstanceDetail/LeaveCalendar）
  views/admin/          管理页（OrgAdmin/FormStudio/SettingsAdmin/AdminLogs/SectorMonitor/FinanceExport）
  components/           form/（设计器子系统）、workflow/（流程编辑）、print/、admin/、layout/、apply/、finance/、instance/
  composables/          31 个组合式函数（useTheme、useNavMenu、useCommandPalette、useFormFormula…）
  utils/                22 个纯函数（workflowFlowGraph、formFormula、serialNoPattern、pdfRender…）
  i18n/bundles/         本地兜底翻译包（远端字典的 fallback）
  styles/               main.css（设计令牌 + 暗色）、form-fill.css、print.css
```

**API 调用是内联的** —— 没有按领域拆分的 api 文件，组件里直接用 `src/api/client.ts` 导出的 `api` 实例。新增接口沿用这个惯例。

**流程设计器不是 LogicFlow。** `components/workflow/wfLogicFlowNodes.ts` 引入了 `@logicflow/core`，但**没有任何地方调用 `registerWfNodes`**，属于历史遗留。真正的设计器是 `WorkflowDesigner.vue` → `WorkflowVerticalDesigner.vue` → `FlowChainEditor.vue` + `FlowConditionLanes.vue` + `WorkflowNodeConfigDrawer.vue`，蛇形网格布局（`useFlowSnakeLayout.ts`，每行 5 个节点）。模型转换在 `utils/workflowFlowGraph.ts`（`flowChainToGraph` / `graphToFlowChain`）。

**设计令牌驱动**：`styles/main.css` 的 `:root` 里定义了 `--brand`、`--bg`、`--surface`、`--text`、`--app-*`（字号、行高、控件高度、圆角、阴影）、`--header-h`、`--sider-w` 等，并**同时覆盖 Arco 自己的 CSS 变量**（`--primary-1..10`、`--gray-1..10`、`--color-bg-*`）。Tailwind 只用于少量工具类（`tailwind.config.js` 仅扩展了 `fontFamily.sans`），不是主要样式手段。

**暗色模式**：`composables/useTheme.ts` 同时设置 `<html data-theme="dark">` 和 `<body arco-theme="dark">` —— 前者驱动自定义令牌，后者驱动 Arco 组件。存储于 `localStorage['imc-theme']`。

**i18n 是后端驱动**：`plugins/i18n.ts` 启动时 `GET /i18n/messages?locale=..&namespaces=..` 拉取扁平 key 字典 → `nestMessages()` 嵌套 → `setLocaleMessage`。带 `X-I18n-Version` 条件请求，服务端可回 **304** 复用 sessionStorage 缓存；**缓存 key 里的 `I18N_BUNDLE_CACHE_ID`（当前 `v28-calendar-holidays`）在 namespace 变更时必须 bump**，否则用户拿到旧缓存。

`src/i18n/bundles/*.ts` 是本地兜底包，合并时**远端优先**，远端值为空或等于 key 时才用本地。文件注释明确要求这些包与 `backend/scripts/seed_i18n_*.py` 保持同步 —— **新增 i18n key 要同时加到后端种子脚本和本地 bundle**。

后台字典维护在 `components/admin/I18nSettingsPanel.vue`（设置页的 i18n tab）：CRUD + `POST /i18n/admin/publish`，publish 后前端会强制刷新词典即时生效。

**嵌入式桌面模式**：前端在 WebView2 里以 `?embed=desktop` 运行，由 `utils/embedDesktop.ts` / `composables/useEmbedDesktop.ts` 处理，路由守卫和布局在嵌入模式下行为不同。

### 桌面客户端

`client/` 是 WPF + WebView2 壳。原生代码只负责：登录窗口（账号密码+图形验证码 / 邮箱验证码）、设备令牌续期、SSE 实时推送（`/api/v1/client/events/stream`）、Windows 桌面通知、托盘气泡、关闭最小化到托盘、开机自启、单实例运行、`tpcworkflow://` 深链接。业务页面全部是嵌入的前端 SPA。

`client/Services/ApiClient.cs` 负责 token 续期与请求包装。首启配置在 `client/appsettings.json`，用户偏好存 `%LocalAppData%\TPCWorkflow\preferences.json`。

发布用 `client/publish.ps1`（`PublishSingleFile` + `SelfContained`），产物复制到 `deploy/downloads/` 供网页下载。

## 部署

生产：nginx `wf.imcsh.com` 把 `/api/` 反代到 `10.1.40.109:5320`（Flask），其余路径到 `:5321`（前端）。配置片段见 `deploy/nginx/wf.imcsh.com.production.patch.conf`，操作步骤见 `deploy/nginx/README.md`。

后端生产环境变量：`BEHIND_PROXY=1`（启用 ProxyFix）、`SESSION_COOKIE_SECURE=1`、`FLASK_DEBUG=0`、`TPC_SKIP_STARTUP_MAINTENANCE=1`。生产**不要**在重启时跑维护，升级后手动跑一次 `scripts/upgrade_db.py`。

## 约定与易错点

- **JSON 字段一律用 `Text` 存**，序列化用 `json.dumps(..., ensure_ascii=False)`。
- 注释、docstring、UI 文案用中文；标识符用英文。
- **RBAC 检查是内联的**，新增路由时自己写 `is_system_admin` / `permissions.py` 判断，别指望有装饰器。
- **静态文件下载只能走 `app/api/uploads.py` 的白名单**（`SERVED_DIRS` / `PUBLIC_DIRS`），并且只允许图片与 PDF 内联渲染，其余一律 `Content-Disposition: attachment`。别再写裸的 `send_from_directory`。
- **通知正文落库前必须脱敏**（`app/utils/mask.py`）：验证码、URL 里的 `token=` 都不能进 `notification_logs.body`。
- **审批人只能改本节点 `field_permissions` 标为 `edit` 的字段**（`node_field_requirements.filter_editable_fields`），前端禁用只是表象，接口层必须再挡一次。
- **`WorkflowEngine._advance` 是节点类型的唯一分派点**，新增节点类型必改。
- **改数据库字段 → 必须同步 `backend/scripts/upgrade_db.py`。**
- **改前端 → 必须 `npm run build`**，Flask 直接托管 `frontend/dist`。
- **新增 i18n key → 后端种子脚本 + 前端 bundle 双写，并 bump 缓存 ID。**
- 后端没装 `requests`（用 `urllib.request`）；没有 pytest（测试是独立脚本）。
- `frontend/src/views/admin/FlowRolesAdminView.vue`、`UsersAdminView.vue` 和 `components/DynamicForm.vue` 是**未被引用的孤儿文件**，已分别被 OrgAdminView 的 tab 和 `components/form/FormRenderer.vue` 取代。
