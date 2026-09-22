# IMC Workflow

企业级工作流系统：Flask + Vue3 + SQLite，支持多组织、运行时国际化、LogicFlow 流程设计器、或签/会签/条件分支、手写签名、多种登录方式。

## 功能清单

| 模块 | 能力 |
|------|------|
| 组织 | 公司、部门、用户任职 |
| 流程角色 | 与系统管理员分离的流程审批角色 |
| 工作流 | 模板设计、发布、发起、待办/已办、条件分支、抄送、转交 |
| 审批 | 或签 / 会签 / 依次、意见必填、手写签名 |
| 国际化 | 管理端维护词典，无需重新编译前端 |
| 登录 | 用户名密码、邮箱+密码、邮箱验证码、短信验证码、Office 365 SSO |
| 系统设置 | SMTP、短信网关、Azure AD 配置 |

## 快速开始

### 后端

```powershell
cd d:\AI\TPCWorkflow\backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
copy .env.example .env
python run.py
```

首次或升级数据库：

```powershell
python scripts\upgrade_db.py
```

默认账号：`admin` / `admin123`（示例公司已配置，含「示例请假」流程）

### 前端开发

```powershell
cd d:\AI\TPCWorkflow\frontend
npm install --registry=https://registry.npmmirror.com
npm run dev
```

### 生产

```powershell
cd frontend
npm run build
cd ..\backend
python run.py
```

## 环境变量（.env）

```ini
SECRET_KEY=change-me
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_REDIRECT_URI=http://127.0.0.1:5173/auth/azure/callback
MAIL_SERVER=
MAIL_USERNAME=
MAIL_PASSWORD=
PUBLIC_BASE_URL=http://127.0.0.1:5173
```

Office 365 登录需在 Entra 注册应用，回调地址与 `AZURE_REDIRECT_URI` 一致。也可在 **系统设置** 页面写入数据库（优先于环境变量）。

## 上传部署示例

```powershell
tar -czf - -C "d:\AI\TPCWorkflow" "backend/app" "backend/config.py" "backend/run.py" "backend/requirements.txt" "backend/scripts" "backend/migrations" "backend/alembic.ini" "frontend/dist" | ssh "david@10.1.40.108" "mkdir -p /tmp/tpcworkflow && tar -xzf - -C /tmp/tpcworkflow"
```

## API 概览

- `POST /api/v1/auth/login` — mode: password | email_code | sms_code
- `GET /api/v1/auth/azure/login-url`
- `GET/PUT /api/v1/admin/settings`
- `GET/POST /api/v1/workflow/definitions`
- `POST /api/v1/workflow/instances` — 发起（含 form / variables）
- `GET /api/v1/workflow/tasks/todo`
- `POST /api/v1/workflow/tasks/{id}/complete`
- `POST /api/v1/uploads/signature` — 手写签 PNG

## 流程图 JSON 约定

节点 `type`：`start` | `approver` | `handler` | `cc` | `condition` | `parallel` | `end`

审批节点 `config`：

```json
{
  "assignee_type": "flow_role",
  "flow_role_code": "dept_leader",
  "apv_rel": "or"
}
```

`apv_rel`：`or` 或签 | `and` 会签 | `sequential` 依次

条件节点 `branches`：

```json
{ "expr": { "field": "form.days", "op": "gt", "value": 3 }, "target": "approve_leader" }
```
