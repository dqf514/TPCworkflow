# IMC Workflow 全站审计报告

> 审计范围：`backend/`（Flask 3 + SQLAlchemy + SQLite）、`frontend/`（Vue 3 + TS + Vite 6 + Arco Design 2.57 + Tailwind 3.4）、`client/`（WPF/WebView2）
> 审计方式：静态代码通读 + Playwright 实机操作（真实登录、11 条路由 × 3 组视口/主题）+ 后端 API 直连验证 + 工作流引擎复现脚本
> 报告日期：2026-11-02
>
> **📌 修复状态见 [第七节](#七修复状态2026-11-02--全修完成)** —— 本节所列 127 项问题（后端 9 / 前端 20 / UI-UX 82 / 美化建议 16）已全部修复，正文保留原始缺陷描述不改写。

---

## 〇、总体结论

| 维度 | 结论 |
|---|---|
| 后端安全 | **存在 1 个可直接拖库/窃密的越权读取，1 个任务详情越权（IDOR），1 条验证码与审批 token 明文入库的链路**。三者可串联成完整攻击链。 |
| 工作流正确性 | **驳回不取消兄弟任务**、**会签人数口径不一致导致实例永久卡死** —— 两条都在真实引擎上复现成功。 |
| 部署可用性 | **`python scripts/upgrade_db.py`（唯一的 schema 迁移途径）在全新库上必崩**，新环境部署流程走不通。 |
| 前端代码 | 20 条真实缺陷，其中 3 条 HIGH（金额大写算法、嵌套条件导出 `target:''`、`text_block` 永不打印）。 |
| UI/UX | 27 条高严重度项，核心是 **Arco 主色覆盖完全失效**（全站两套主色）与 **暗色模式硬编码白底**。 |
| 设计令牌 | 令牌体系本身建得不错，但 **落地率 < 3%**，视觉一致性目前靠散落的 px 维持。 |

---

## 一、致命问题（均已在运行中的系统上实测复现）

### 1.1 【CRITICAL】任意登录用户可下载整个 SQLite 数据库、.env 和全部后端源码

**位置**：`backend/app/api/uploads.py:111-126`

```python
@files_api.route('/<path:subpath>', methods=['GET'])
@login_required
def serve_file(subpath):
    base = _project_base()                       # = backend/
    norm = subpath.replace('\\', '/').replace('..', '')
    full = os.path.join(base, norm)              # ← 只过滤 '..'，不限制目录范围
    ...
    return send_from_directory(directory, os.path.basename(full))
```

`serve_file` 只有 `@login_required`，**没有任何目录白名单，也没有任何权限位校验**；唯一的过滤是把 `..` 删掉，等于「`backend/` 目录下的任意文件都能下载」。

**实测**（任意登录会话）：

| 请求 | 结果 |
|---|---|
| `GET /api/v1/files/data/tpcworkflow.db` | **200，2 654 208 字节**，首字节 `SQLite format 3` |
| `GET /api/v1/files/.env` | **200**，返回 `SECRET_KEY=change-me` 等全部内容 |
| `GET /api/v1/files/app/__init__.py` | **200**，后端源码 |
| `GET /api/v1/files/scripts/upgrade_db.py` | **200**，16 275 字节脚本 |
| `GET /api/v1/files/requirements.txt` | **200** |

**影响**：数据库里装着全公司员工的 `password_hash`（`models/user.py:16`）、LLM 服务商 API Key（`models/llm_provider.py:23`）、SMTP 凭据、所有报销单与合同金额、通知日志里的登录验证码与邮件审批 token（见 1.2）。**任何一个普通员工的账号被拿到，就等于拖库。**

**修复**：

```python
_ALLOWED_PREFIXES = ('uploads/attachments/', 'uploads/avatars/', 'uploads/signatures/', 'uploads/branding/')

@files_api.route('/<path:subpath>', methods=['GET'])
@login_required
def serve_file(subpath):
    norm = subpath.replace('\\', '/').lstrip('/')
    if not norm.startswith(_ALLOWED_PREFIXES):
        return fail('无权访问', status=403)
    full = os.path.abspath(os.path.join(_project_base(), norm))
    if not full.startswith(os.path.abspath(_project_base()) + os.sep):
        return fail('无权访问', status=403)
    ...
```

另外 `/api/v1/public/files/<path>`（`uploads.py:97-108`）虽已限定 `uploads/branding/` 前缀，但同样应加上 `os.path.abspath` 校验，避免软链/相对路径绕过。

---

### 1.2 【CRITICAL】登录验证码与邮件审批 token 明文入库，且可通过日志接口读出

**位置**：`backend/app/api/admin_logs.py:254-289`（返回 `body` 全文）、`backend/app/services/notify.py`（写入 `NotificationLog.body`）

**实测**：库里 42 条通知日志中 **21 条正文含明文验证码或审批 token**。

```
login_code  email  floradong@imc-shipmanagement.com
您的登录验证码为：931127，10 分钟内有效。

approval_notify  daviddu@tsaopaochee.com
快速处理（链接 7 日内有效，仅可使用一次）：
  同意：https://wf.imcsh.com/api/v1/workflow/tasks/email-action?token=kwPa4RucPON3B5GoheFQ5vumMlzw7GVyywx_0SR-oCw
  驳回：https://wf.imcsh.com/api/v1/workflow/tasks/email-action?token=EfeEza9i...
```

**串联攻击**（结合 1.1）：普通员工 → 下载 `tpcworkflow.db` → 读 `notification_logs.body` → 拿到他人**正在使用的一次性登录验证码**与**待办审批 token** → 冒名登录 / 直接替他人「同意、驳回」。

**修复**：
- 落库前对 `body` 做脱敏（验证码、token 用 `***` 替换），或只存模板 + 变量而非渲染后的正文；
- `logs/notifications` 接口不再返回 `body`，或对 `login_code` / `approval_notify` 类型强制脱敏；
- 已落库的历史记录需要一次清理脚本。

---

### 1.3 【HIGH】任务详情越权（IDOR）：任意登录用户可读取任意审批任务及其实例

**位置**：`backend/app/api/workflow.py:1189-1195`

```python
@workflow_api.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    task = TaskInstance.query.get(task_id)
    if not task:
        return fail('任务不存在', status=404)
    return ok(_task_dict(task, detail=True))     # ← 无 assignee / 参与者 / 实例可见性 校验
```

对比同文件的 `GET /api/v1/workflow/instances/<id>` 会走 `instance_access.py` 的可见性判定；**这条路径完全绕过了它**。

**实测**（以普通员工「蒙军」登录，`can_view_instances=False`）：

```
GET /api/v1/workflow/tasks/10  → 200
{
  "assignee_id": 16, "instance_id": 6,
  "instance": {
    "display_no": "2026-08-18-0002",
    "initiator_name": "赵玉冰",
    "total_amount": 2071.38,
    "company_name": "万邦船舶管理（上海）有限公司",
    "department_name": "财务部（Fin）",
    "public_uuid": "718f5424-1320-46fb-8ccf-9394fcf00c29",
    ...
  }
}

GET /api/v1/workflow/instances/6  → 404「流程不存在」   ← 正确拦截
```

**影响**：任务 ID 是自增整数，可直接遍历。员工 A 可读到员工 B 的报销单金额、收款银行账号（`field_4_8vm4` 里就有）、公司/部门结构，以及 `public_uuid`（本应只对参与者公开的实例访问凭据）。

**修复**：在 `get_task` 中复用 `instance_access` 的判定，例如

```python
if task.assignee_id != current_user.id and not user_can_view_instance(current_user, task.instance):
    return fail('无权访问', status=403)
```

---

### 1.4 【HIGH】驳回不取消同节点兄弟任务 → 已驳回的实例能被翻成「已通过」

**位置**：`backend/app/services/workflow_engine.py:240-246`

```python
if action != 'approve':
    inst.status = 'rejected' if action == 'reject' else action
    inst.finished_at = datetime.now()
    inst.current_node_ids = json.dumps([])
    db.session.commit()          # ← 没有把其它 pending 任务置为 cancelled
    notify_instance_result_if_finished(...)
    return inst
```

同一文件里加签分支的驳回处理（`:359-366`）**是**做了取消的：

```python
if action == 'reject':
    inst.status = 'rejected'
    ...
    for t in inst.tasks.filter_by(status='pending').all():
        t.status = 'cancelled'
```

而 `_continue_after_task_approved`（`:392-432`）也**没有** `inst.status` 的守卫，`complete_task` 只校验 `task.status == 'pending'`（`:116`）。

**实测复现**（或签节点，A/B 两人）：

```
待办任务: 18 19
驳回后 instance.status = rejected | B 的任务状态 = pending     ← 兄弟任务未被取消
>>> B 仍能在待办里看到该任务
B 同意后 instance.status = approved                            ← 已驳回的实例被翻成 approved
```

**影响**：或签/会签节点里，只要有人驳回，其他审批人的待办不会消失；他们点「同意」即可把已被驳回的单据重新推进到「已通过」，**审批结论被推翻，审计轨迹与最终状态不一致**。会签场景更严重 —— 任一驳回都应终止整单。

**修复**：在主分支的驳回处理里补上取消：

```python
if action != 'approve':
    inst.status = 'rejected' if action == 'reject' else action
    inst.finished_at = datetime.now()
    inst.current_node_ids = json.dumps([])
    for t in inst.tasks.filter_by(status='pending').all():
        t.status = 'cancelled'
        t.completed_at = datetime.now()
    db.session.commit()
```

并在 `complete_task` 开头补一道实例状态守卫：`if inst.status in ('rejected', 'cancelled', 'withdrawn'): raise ValueError('流程已结束')`。

---

### 1.5 【HIGH】会签人数统计口径不一致 → 实例永久卡死（无人能推进）

**位置**：`backend/app/services/workflow_engine.py:431-448`

```python
approved = inst.tasks.filter_by(node_id=node_id, status='approved').count()
resolver = AssigneeResolver(inst)
needed = len(resolver.resolve(node.get('config') or {}))   # ← 用「原始解析结果」当应到人数
return approved >= needed and needed > 0
```

但真正建任务时走的是 `workflow_task_utils.resolve_assignees_for_node`（`:31-80`），它会**减少**人数：
- `filter_active_assignees(raw_ids)` —— 剔除离职/停用用户；
- `apply_dept_manager_skip_policy` —— 唯一经理是发起人时跳过，或剔除发起人防自审；
- `approver_resigned_action` —— 离职转交时只保留 1 人。

于是 `needed` 永远 ≥ 实际创建的任务数，**会签永远凑不齐**。

**实测复现**（2 人会签，其中 1 人停用）：

```
创建的任务数: 1 [2]  期望会签人数=2
全部同意后 instance.status = running | 剩余 pending 任务: 0
```

实例卡在 `running`，**没有任何待办任务**，任何人都无法再推进它 —— 一张永久僵尸单据。

**修复**：用与建任务同一口径的应到人数。最稳妥的做法是在建任务时把「本节点应到人数」写进任务元数据（如 `action_meta['expected_approvers']`），`_node_approved` 直接读它，不再二次解析（角色成员变更后二次解析同样会算错）。

---

### 1.6 【HIGH】`python scripts/upgrade_db.py` 在全新数据库上必崩 —— 新环境部署走不通

两个**独立**的原因叠加，实测复现：

**原因 A —— 种子数据里同一个 key 定义了两次**
`backend/scripts/seed_i18n_settings.py:21` 与 `:171` 都定义了 `('settings', 'opt_panel_desc_option', ...)`（值不同）：

```
21:  ('settings', 'opt_panel_desc_option', '维护下拉框、单选等控件的选项（名称 + 编码）；表单设计时关联「选项配置表」'),
171: ('settings', 'opt_panel_desc_option', '维护下拉框等控件共用的选项配置表；表单设计时关联「选项配置表」'),
```

`scripts/seed_i18n_zh_cn.py` 把 `SETTINGS_ZH` 汇总进 `SEED_MESSAGES`（966 条），于是同一个唯一键出现两次。而 `scripts/bootstrap.py:237-246` 是**无存在性检查的批量插入**：

```python
for namespace, msg_key, msg_value in SEED_MESSAGES:
    db.session.add(I18nMessage(namespace=namespace, msg_key=msg_key, locale='zh-CN', msg_value=msg_value))
db.session.commit()      # ← executemany 批量里带重复唯一键 → IntegrityError
```

**原因 B —— `upgrade_all()` 的调用顺序**
`backend/scripts/upgrade_db.py:356-357`：

```python
added = seed_all_locales()      # 先插入全部 zh-CN / en-US 词条
ensure_bootstrap()              # 再 bootstrap → _ensure_locales() 判定"没有 locale" → 又插一遍 966 条
```

`bootstrap._ensure_locales()` 的守卫是 `if I18nLocale.query.count(): return`（`bootstrap.py:220`）—— 新库里 locale 确实为 0，守卫放行，于是把已被 `seed_all_locales()` 插入的 966 条又插一遍。

**实测**：

```
$ DATABASE_URI=sqlite:///.../_fresh.db python scripts/upgrade_db.py
sqlalchemy.exc.IntegrityError: (sqlite3.IntegrityError)
UNIQUE constraint failed: i18n_messages.namespace, i18n_messages.msg_key, i18n_messages.locale
  [SQL: INSERT INTO i18n_messages (...) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id]
```

验证修复方案（两处都改才有效）：

- 删掉 `scripts/seed_i18n_settings.py:171` 的重复项（或让 `seed_i18n_zh_cn.py` 汇总时按 `(ns, key)` 去重）；
- `upgrade_db.upgrade_all()` 改成**先 `ensure_bootstrap()` 再 `seed_all_locales()`**；
- 建议把 `bootstrap._ensure_locales()` 的守卫从 `I18nLocale.query.count()` 改成 `I18nMessage.query.count()`，并给那 966 条插入加上按 key 的存在性判断。

实测：两处都改后，新库 `ensure_bootstrap()` + `seed_all_locales()` 一次通过（`added 0`）。

> 附带影响：现存库里生效的是**第一条**的值，而前端 bundle `frontend/src/i18n/bundles/settings.ts:171` 用的是同一条 —— 所以线上显示是对的，但种子脚本与 bundle 的字面量已经不一致，后续谁改了任一边就会出现「远端字典优先、本地兜底」下的文案漂移。

---

### 1.7 【HIGH】生产环境 SECRET_KEY 是仓库里的公开常量，可伪造管理员会话

**三个事实叠加**：

1. `backend/config.py:18` —— `SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-change-me-in-production')`，**默认值写死在仓库里**；
2. `backend/.env.example` 与根 `README.md:57` 都写 `SECRET_KEY=change-me`；
3. `deploy/nginx/README.md` 的「后端环境变量」清单里**只有** `BEHIND_PROXY / SESSION_COOKIE_SECURE / FLASK_DEBUG / TPC_SKIP_STARTUP_MAINTENANCE` —— **没有 SECRET_KEY**。照着部署文档做，Flask 会用上面那个公开默认值。

另外 `python-dotenv` 装了但**全项目没有任何一处调用 `load_dotenv()`**（`grep -rn "load_dotenv" backend/` 无结果）—— **`.env` 是个死文件**，写在里面的一切都不会生效（这本身也是一条独立的部署陷阱，见 1.8）。

**实测**：用 `change-me` 签名伪造的 session cookie 被线上服务器直接接受：

```
Cookie: session=eyJfdXNlcl9pZCI6IjEiLCJfZnJlc2giOnRydWUsIl9pZCI6IngifQ...
GET /api/v1/auth/me  →  200  {"data": {"auth_provider": "local", ...}}
```

拿到管理员会话后，`/api/v1/files/data/tpcworkflow.db`（1.1）就变成「任何人拖库」。

**修复**：
- `config.py` 启动时强制校验：`SECRET_KEY` 为默认值/短于 32 位时，生产环境直接 `raise RuntimeError`；
- `deploy/nginx/README.md` 的环境变量清单补上 `export SECRET_KEY=$(openssl rand -hex 32)` 并写明「必须固定，重启不变」；
- 若确实要支持 `.env`，在 `create_app()` 里加 `load_dotenv()`（`python-dotenv` 已在依赖里）。

---

### 1.8 【MEDIUM】`.env` 从不被加载 —— 文档里的生产配置全部静默失效

`backend/requirements.txt:6` 有 `python-dotenv`，但 `grep -rn "load_dotenv" backend/` 无任何结果，`config.py` / `run.py` / `app/__init__.py` 全部只读 `os.environ`。

于是 `CLAUDE.md` 与 `deploy/nginx/README.md` 里「`copy .env.example .env`」「`.env` 设 `SESSION_COOKIE_SECURE=1`」「`.env` 设 `BEHIND_PROXY=1`」这些指引**都是无效的**。`config.py:19` 的注释「生产 HTTPS 反代：.env 设 SESSION_COOKIE_SECURE=1」尤其误导。

**修复**：二选一 —— 要么在 `create_app()` 开头 `load_dotenv()`，要么把文档里的 `.env` 全部改成 `export` / systemd `EnvironmentFile=`。

---

### 1.9 【MEDIUM】审批人可越权改写任意表单字段（mass assignment）

**位置**：`backend/app/services/workflow_engine.py:155-159`、`backend/app/api/workflow.py:1206-1216`

```python
if form_update and action == 'approve':
    merged = dict(original_form)
    merged.update(form_update)          # ← 不做任何字段白名单/权限过滤
    variables['form'] = merged
```

节点级的 `field_permissions`（每个字段 `edit` / `view` / `hidden`）**只**在 `app/services/node_field_requirements.py:82,161` 用来决定「哪些字段做必填/须修改校验」，**从不用于限制哪些字段可以被写入**（`grep -n "field_permissions" app/services/workflow_engine.py` 无结果）。API 层也只是把客户端传来的 `data['form']` 原样合并。

**影响**：一个节点上被配置为「只读」的字段（例如金额、收款账号），审批人只要在请求体里带上该 key 就能改写。前端 UI 会隐藏这些字段，但接口层不拦。

**修复**：在合并前按 `node_config['field_permissions']` 过滤，只允许 `edit` 的字段进入 `merged`；不允许的字段若出现在请求里应当直接报错而不是静默忽略。

---

### 1.10 后端已核查确认无问题的部分

- **路由鉴权矩阵**：193 个 `/api` 路由全部扫过。除 `/api/v1/i18n/locales`、`/api/v1/i18n/messages`（登录页需要，公开合理）、`/api/v1/workflow/tasks/email-action`（一次性 token 鉴权，公开合理）、`/api/v1/public/files/*`（已限定 `uploads/branding/` 前缀）外，**其余全部有 `login_required` 或管理员校验**，没有裸奔的管理接口。
- **SQL 注入**：`app/services/` 下没有字符串拼接的 `execute()` / `text(f"...")`；参数全部走绑定参数。
- **路径穿越**：`..` 已被剥离，且 `send_from_directory` 只接受 basename，实测 `../` 与 URL 编码穿越均返回 404（但见 1.1 的目录范围问题）。
- **`complete_task` 的执行人校验**：`workflow_engine.py:118` `if task.assignee_id != actor_id: raise ValueError('无权处理该任务')` —— 审批动作本身鉴权正确（只有**查看**任务详情漏了）。
- **邮件快捷审批**：一次性 token、过期校验、单次使用标记、`confirm=yes` 二次确认俱全。
- **schema 同步**：把 43 张表、全部模型列与运行中的库逐列比对，**没有发现模型有、库里缺的列**，`upgrade_db.py` 的 `_ensure_columns` 覆盖是完整的。
- **两个孤儿文件**：`views/admin/FlowRolesAdminView.vue`、`views/admin/UsersAdminView.vue`、`components/DynamicForm.vue` 未被引用（已在 CLAUDE.md 记录），其中 `UsersAdminView.vue:139` 仍有 `api.delete` 调用，属死代码。

---

## 二、前端代码缺陷（20 条：HIGH 3 / MEDIUM 10 / LOW 7）

### HIGH

**F1. 金额中文大写算法错误，所有小金额打印成「零壹佰」**
`frontend/src/utils/printFormat.ts:151-171`（`convertUnder10000`）
补零产生的前导 0 也会置 `zero=true`，导致第一个非 0 位前多补一个「零」；`d===1 && unit==='拾' && !s` 在 `s` 已写成「零」之后才求值，「壹拾」永远输出成「零壹拾」。负数会索引出 `CN_DIGITS[-1]` → `undefined`。

| 金额 | 实际输出 | 应为 |
|---|---|---|
| 1 | `零壹元整` | `壹元整` |
| 10 | `零壹拾元整` | `壹拾元整` |
| 500 | `零伍佰元整` | `伍佰元整` |
| 10000 | `零壹万元整` | `壹万元整` |
| -500 | `undefined仟伍佰元整` | — |

调用链：`printFormat.ts:195 formatMoneyPrint` → `usePrintFormData.ts:200/373` → `WorkflowPrintSheet.vue` 页脚金额。中文环境必然触发。

**F2. 分支内嵌套条件导出为 `target: ''`，流程引擎无法路由该分支**
`frontend/src/utils/workflowFlowGraph.ts:449-467`
`flowChainToGraph` 递归导出子条件时找不到 `type:'start'` 节点（`start` 只在 `graphToFlowChain:294-299` 补），`nestedStart` 恒为 `undefined` → `firstId` 保持 `''` → `branchesOut.push({..., target: ''})`。后端 `resolve_next_node_ids` 拿不到后继 → **该分支永远不会被命中，流程走到条件就断链**，同时设计器预览图上多出一个无入边的孤立节点。

**F3. `text_block` 字段永远不会打印**
`frontend/src/composables/usePrintFormData.ts:333`（配合 `:311`、`:403`）
`buildPrintSections` 初始化 `textBlocks: []` 后对 `field.type === 'text_block'` 直接 `continue`，**没有任何一处 push**；而 `WorkflowPrintSheet.vue:89` 渲染的正是 `block.textBlocks`。表单上能看到、打印件上静默消失。

### MEDIUM

| # | 问题 | 位置 | 失败场景 |
|---|---|---|---|
| F4 | 分支「排序后下标」被当作数组下标 | `FlowConditionLanes.vue:210-222` + `WorkflowVerticalDesigner.vue:141-160,225-232` | 改了 priority 后，泳道图上第二行（显示 B2）实际编辑/删除的是 B1 |
| F5 | 申请页一进入就是「未保存」 | `ApplyFlowView.vue:681-682` + `FormRenderer.vue:467-483,504-515,790-798` | 含 `user_picker`/`dept_picker` 默认值时，用户没动过点返回也弹「有未保存的修改」 |
| F6 | ISO 带时区时间不做本地化转换 | `utils/dateTime.ts:7-10` | `new Date().toISOString()` 生成的 `printedAt` 在 UTC+8 下打印时间差 8 小时 |
| F7 | i18n 缓存解析/存储写入无异常保护 | `plugins/i18n.ts:117,179,184` + `main.ts:20-21` | sessionStorage 缓存被写坏 → `JSON.parse` 抛错 → `bootstrap()` reject → **整站白屏**；隐私模式下 `localStorage.setItem` 抛错同样白屏 |
| F8 | 发布流程忽略保存失败 | `views/admin/FormStudioView.vue:1036-1038` | `saveAll()` 失败仍继续 publish → **把旧版本发布出去并提示成功** |
| F9 | 表单定义列表加载无 catch | `FormStudioView.vue:697-703,930-937` | 500/断网 → spinner 永远转、无任何提示 |
| F10 | 转办失败无任何提示，弹窗不关 | `TaskDetailView.vue:635-643` | 失败 = unhandled rejection + 弹窗原地不动，用户以为已转办 |
| F11 | 待办/已办列表加载无 catch | `TasksView.vue:351-371,373-394` | 接口 500 → 列表空白，**用户误以为「我没有待办」** |
| F12 | 节点配置抽屉选项加载产生未捕获异常 | `WorkflowNodeConfigDrawer.vue:857-881` | `/admin/flow-roles` 403 → 下拉为空且无提示 |
| F13 | `router.afterEach` 在组件里注册且不注销 | `layouts/AppLayout.vue:394-396` | 登出/登录 5 次后叠加 5 个钩子 → 待办角标请求量成倍增长 + 闭包泄漏 |

### LOW

| # | 问题 | 位置 |
|---|---|---|
| F14 | 无金额的实例在仪表盘显示为 `¥0.00`（后端明确返回 `None`） | `DashboardView.vue:310-318` |
| F15 | 表单设计器拉取已发布表单列表无 catch | `components/form/FormDesigner.vue:916-929` |
| F16 | `pickSingleNext` / `findMergeAfterCondition` 存在恒等分支，判定逻辑失效 | `utils/workflowFlowGraph.ts:146-149,196` |
| F17 | `exportSegmentChain` 是与 `flowChainToGraph` 重复且语义相反的死代码（返回链尾却当链首用） | `utils/workflowFlowGraph.ts:330-387` |
| F18 | 新增条件分支时数值数组 splice 用了已变更的长度 | `WorkflowNodeConfigDrawer.vue:790` |
| F19 | `nestMessages` 遇到「叶子键 + 同名前缀键」会互相覆盖 | `plugins/i18n.ts:19-32` |
| F20 | 自定义打印模板的货币显示硬编码 `($)`（CNY 也显示 `CNY ($)`） | `components/print/ConfigurablePrintSheet.vue:134-138` |

---

## 三、UI/UX 缺陷

### 3.1 高严重度（27 项，核心 12 项）

| 类别 | 位置 | 问题 | 影响 |
|---|---|---|---|
| **D 视觉一致性 / E 暗色** | `styles/main.css:92-112` | `:root` 里定义的 `--primary-1..10`、`--gray-1..10` **完全失效**。Arco 把同一批变量声明在 `body { }` 上（`node_modules/@arco-design/web-vue/dist/arco.css`），body 自身的声明优先于从 `:root` 继承的值 | **全站两套主色**：按钮是品牌紫 `#5034ff`，日历选中、复选框、Slider、Tabs 墨条、菜单选中、Steps 等 129 个选择器仍是 Arco 蓝 `#165DFF`。实测 `html --primary-6 = 80,52,255` 而 `body --primary-6 = 22,93,255` |
| **E 暗色模式** | `views/admin/OrgAdminView.vue:1107,1142` | `color: #1d2129` 硬编码 | 组织架构页暗色模式下整棵部门树节点名**几乎不可见（对比度约 1.1:1）**，而次要的「负责人：秦晋」反而清晰 —— 层级颠倒。实测桌面端「负责人：秦晋」和「4 人/8 人」标签在面板边缘**硬裁切半个字** |
| E 暗色 | `views/admin/FormStudioView.vue:1270-1271` | `background:#fff; border:1px solid #e5e6eb` | 属性面板暗色下仍是白卡片 |
| E 暗色 | `styles/print.css:59-61,72-74` | `rgba(255,255,255,0.96)` / `#fff` + `#1d2129` | 打印预览固定底栏是刺眼白条 |
| E 暗色 | `components/print/WorkflowPrintPreviewOverlay.vue:152,162-171,185-187` | `#eef0f3` 全屏遮罩、`#fff` 头部、`#fff7e8/#ffcf8b/#ff7d00` 警告横幅 | 打印预览一打开整屏变亮，是全站最刺眼的暗色破口 |
| E 暗色 | `components/workflow/FlowNodeCard.vue:124,205` | `background:#fff` + `color:#1d2129` | 流程设计器节点卡白底黑字 |
| E 暗色 | `WorkflowNodeConfigDrawer.vue:942` / `FlowConditionLanes.vue:238,400` / `FlowAddMenu.vue:55,85,105` / `AttachmentPreviewPanel.vue:312,417,431,451,496` / `ProcessIconPicker.vue:45` / `FormRenderer.vue:923` / `LeaveCalendarField.vue:462,620,638` | 一律硬编码 `#fff` / `linear-gradient(#fafbfc→#fff)` | 表单填报区、附件预览、日历控件、流程画布在暗色下都有白块 |
| **A 可访问性** | `views/LoginView.vue:93,101,126,134` | `hide-label` 会把 `<label>` **整个从 DOM 移除**（Arco `es/form/form-item.js:398`），不是视觉隐藏 | 登录页 4 个输入框**完全没有可访问名称**，读屏只念 placeholder |
| A 可访问性 | 全站 60+ 个 `a-form-item`（`ProfileModal.vue:12-62`、`FormDesigner.vue:158-446`、`WorkflowNodeConfigDrawer.vue:26-111`、`OrgUsersPanel.vue:61-99` …） | Arco 的 `FormItemLabel` **从不输出 `for`**，只能靠 `field` 推导 id，但全站都没传 `field`/`prop` | label 与控件无程序化关联：点击 label 不聚焦、读屏不播报字段名、`:required` 只画红星号不触发校验 |
| A 可访问性 | `components/workflow/FlowNodeCard.vue:2-9` | 节点卡是 `<div @click>`，无 `role`/`tabindex`/键盘事件 | 设计器最核心的「点节点改配置」**键盘完全不可达** |
| A 可访问性 | `components/form/FormDesigner.vue:63,91,354` | 可点击 div 无 `role`/`tabindex` | 表单设计器无法用键盘选中字段/分区/明细列 |
| A 可访问性 | `OrgAdminView.vue:1239` / `OrgUsersPanel.vue:723` | `.admin-mail-input { outline: none }`，`:focus` 只改颜色 | **键盘焦点完全不可见**，违反 WCAG 2.4.7 |
| A 可访问性 | `views/MyInstancesView.vue:35-39` | 未读状态仅用纯色圆点表达 | 颜色是唯一状态载体（违反 WCAG 1.4.1），`title` 仅 hover 可见 |
| **B 响应式** | `components/MobileTabBar.vue:3` vs `layouts/AppLayout.vue:84,96,115` | TabBar 用 Tailwind `md:hidden`（≥768 隐藏），AppLayout 用 `isMobile`（`useBreakpoint.ts:4` = `max-width:1023px`） | 768–1023px 平板：标签栏被渲染但被隐藏，而 `.app-content.has-mobile-tab .app-content-inner` 仍留 `padding-bottom:56px` → **平板上每页底部凭空多一块空白**（实测 900px 视口确认） |
| B 响应式 | `views/TaskDetailView.vue:266` | `hasMobileTabBar = width.value < 768` | 768–1023px 上固定操作栏（`z-index:55`）**完全盖住**底部标签栏（`z-index:50`），标签栏不可点 |
| **C 交互反馈** | `views/TaskDetailView.vue:635-643,77` | 转办无 try/catch、无 loading、弹窗无 `:ok-loading` | 转交失败 = 静默无反应 |
| C 交互反馈 | `components/form/FormRenderer.vue:789-797` 与 `:802-816` | 双向 deep watch 回环：model → emit → props → `Object.assign` → model | 长表单每次击键全表浅拷贝 + 重算公式 + 联动清理，**明显卡顿且有无限回环风险** |
| C 交互反馈 | `components/form/FormDesigner.vue:151-156,1187,1196` | `:key="propsPanelKey"` 挂在整个 `<a-form>` 上，每选一次字段就自增 | 属性面板被整体销毁重建 → **输入框失焦、滚动位置丢失** |
| C 交互反馈 | `components/form/FormDesigner.vue:1200-1205,1232-1246,899-905` | 删除字段/分区/明细列**均无二次确认**（而 `FlowNodeCard.vue:12-22`、`WorkflowNodeConfigDrawer.vue:357-363` 都用了 `a-popconfirm`） | 误触即永久丢失配置，且同项目内策略自相矛盾 |
| **G 性能** | `components/form/AttachmentPreviewPanel.vue:90` → `utils/pdfRender.ts:1` | 静态 `import` 引入 pdfjs（`build/pdf.mjs` **843 KB**）；`PrintPdfPages.vue:54` 已正确用动态 import，但被这条静态导入抵消 | **所有表单页首屏都要下载 800KB+ 无用代码** |
| D 视觉一致性 | `layouts/AppLayout.vue:776` | `color: var(--text-muted);` —— **`--text-muted` 在 main.css 中不存在**（真实令牌是 `--text-tertiary`） | 声明在计算值阶段失效，颜色回退为继承值（全项目唯一一处） |

### 3.2 中严重度（约 40 项，核心 25 项）

| 位置 | 问题 |
|---|---|
| `workflow/WorkflowNodeConfigDrawer.vue:5` | `:width="520"` 固定抽屉宽，无 `max-width:100vw` → 375px 视口横向溢出 |
| `components/ProfileModal.vue:96` | `modalWidth = 880 \| 520`，880px 弹窗在手机上不可用 |
| `components/form/FormDesigner.vue:1260,1304-1310` | `grid-template-columns: 248px 1fr 560px` 固定三栏，≤1280px 未降列 → 属性面板被压到每列 ~160px |
| `workflow/FlowChainEditor.vue:130-137` + `FlowNodeCard.vue:115-117` | `.flow-row { flex-wrap: nowrap }`，节点卡宽 150px → 一行 5 节点 ≈750px，375px 必横向溢出 |
| `workflow/FlowChainEditor.vue:147-153` | `.flow-row-break { margin-left: 75px }` 与实际节点宽 150px 不符 → 蛇形折返连接线错位 |
| `print/WorkflowPrintPreviewOverlay.vue:230-241` | `.wf-print-preview-doc { max-width: 210mm }` ≈794px → 手机端只能横向滚动 |
| `styles/print.css:99-102` | `@page { size: A4 portrait }` 硬编码 → 模板的 `orientation`/`pageSize` **全部失效** |
| `layouts/AppLayout.vue:59-60` | `@change` 与 `@update:model-value` 同时绑 `onLocaleChange` → 切一次语言触发两次拉取 + 两次 `PATCH /auth/me` |
| 全局（`router/index.ts` 无 `scrollBehavior`） | 滚动容器是 `.app-content`（`overflow-y:auto`），路由切换不复位 → **从长列表滚到底再进详情，新页面从中部开始显示** |
| `views/admin/SettingsAdminView.vue:649-652,699-702` | `removeSector`/`removeScoped` 无 try/catch、无提示 → 删除失败界面零反馈 |
| `workflow/WorkflowNodeConfigDrawer.vue:366` | 保存按钮无 `:loading`/`:disabled` → 可重复提交 |
| `workflow/WorkflowNodeConfigDrawer.vue:509-513` | 跳转目标下拉 `label` 直接用内部 node id → 用户看到 `node_1712...` |
| `views/DashboardView.vue:323-344` | `Promise.allSettled` 只处理 `fulfilled`，`rejected` 静默丢弃 → 三个接口全挂时显示「没有待办」而非错误态 |
| `components/layout/CommandPalette.vue:5,8-20,26-40` | 无 `role="combobox"`/`aria-expanded`/`listbox`/`option`，无焦点陷阱 → 读屏无法播报高亮项，Tab 会跳到遮罩后元素 |
| `print/WorkflowPrintPreviewOverlay.vue:3-77` | 全屏浮层无 `role="dialog"`/`aria-modal`、无焦点陷阱、无 Esc 关闭 → 键盘用户打开后**无法退出** |
| `components/form/AttachmentPreviewPanel.vue:2-5` | 有 `role=dialog aria-modal` 但无 keydown 监听、无 focus() → 名不副实 |
| `components/NavBadge.vue:6` | `aria-hidden="true"` → 待办徽标数字对读屏完全不可闻 |
| `workflow/ApprovalTimeline.vue:2` | `v-if="items.length"` 无 else → 审批记录为空时整块消失，无「暂无记录」 |
| `workflow/StatusPill.vue:37,51-53` | `label` 兜底返回英文枚举（`withdraw`/`transfer`）；截断后无 `title` → 中文界面出现英文状态 |
| `styles/main.css:604` | `.stat-card-accent { border-color:#e6e0ff }` 硬编码，暗色无覆盖 → 亮边暗底 |
| `styles/main.css:452` | 固定列阴影 `rgba(23,25,27,0.18)` 写死 → 暗色下不可见，固定列与滚动列无分隔 |
| `styles/main.css:414` vs `styles/form-fill.css:119` | 焦点环两套实现（`rgba(80,52,255,.16)` vs `var(--brand-soft)`）→ 表单页焦点环几乎不可见 |
| 令牌采用率 | `--app-space-section` 3 次、`--app-space-card` 1 次、`--app-control-h-sm` 0 次、`--shadow-md` 0 次；同时 47 处裸 `box-shadow`、13 处非标圆角、20+ 种 padding 组合 → **令牌体系形同虚设** |
| 字号碎片化 | `12px`×60 与 `0.75rem`×25、`13px`×31 与 `0.8125rem`×28、`14px`×12 与 `0.875rem`×14 → 同一字号 2–3 种写法 |
| 字重 | `650`×8、`550`×6 → `PingFang SC`/`Microsoft YaHei` 无此字重，macOS/Windows 渲染不同 |
| `components/BrandLogo.vue:95` | 暗色下 `color:#fff` 落在 `--brand`(#8a76ff) 上，对比度约 **3.45:1** < AA 4.5:1 |
| `styles/main.css:143`（暗色 `--brand:#8a76ff`） | `--brand` 作正文色对比度约 **4.47:1** → 全站选中态文字勉强不达标 |
| `workflow/WorkflowProgressPanel.vue:10-28`、`FlowChainEditor.vue:2-70`、`ConfigurablePrintSheet.vue:43-78`、`WorkflowNodeConfigDrawer.vue:174-220` | 四处空数据只渲染标题/空白画布/空表头，缺「暂无数据」提示 |
| `workflow/WorkflowInstanceList.vue:258` | `<a-empty v-if="!rows.length" />` 无 `description` → 中文界面出现英文 "No Data" |
| `components/form/FormRenderer.vue:640-657` | `preloadFieldOptions()` 串行 await → N 个字段 = N 次串行网络往返瀑布 |
| `components/form/LeaveCalendarField.vue:5-8` | FullCalendar + daygrid + 2 locale 被静态引入 FormRenderer → 任何表单页都带上日历包 |
| `components/form/FormDesigner.vue:931-934,983-986` | `schemaFingerprint()` 每次父级回写都整份 `JSON.stringify` → 大表单编辑时开销显著 |
| `print/WorkflowPrintSheet.vue:46,58,109,119` 等 | 大量 `v-for` 用索引作 `:key` → 数据重排时渲染错位 |
| `utils/printFormat.ts:18,19,24,200,245` 等 | 货币符号 `￥`(U+FFE5) 与 `¥`(U+00A5) 混用，且 `DetailField.vue:61` 还写成 `¥ 1,234.56`（带空格） |
| `utils/printFormat.ts:24` | `JPY: '￥'` → 日元与人民币同形，日元凭证金额会被误读 |
| `components/form/MoneyField.vue:225-227`、`PlainAmountField.vue:41-44` | 金额只 `text-align:right`，缺 `font-variant-numeric: tabular-nums`（`main.css:571` 已有该工具类未用）→ 金额列无法竖向对齐 |
| `components/form/FormRenderer.vue:290` vs `workflow/ApprovalTimeline.vue:15` | 打印审批记录表直接输出 `t.action` 原始英文枚举 → 同一份轨迹，页面是「已通过」，打印件是 `approved` |
| `components/print/ConfigurablePrintSheet.vue:45,73,137` | `\|\| 'PARTICULARS'`、`\|\| 'Total'` 英文兜底 → 中文财务凭证出现 `CNY ($)`、英文表头 |
| 硬编码中文 | `ProfileModal.vue`（多处）、`TaskDetailView.vue:40,54,73,77,117`、`LoginView.vue:98,104,148`、`FinanceExportView.vue`、`SectorMonitorView.vue:17`、`FormStudioView.vue:241,247,253` | 应用有语言切换器，但这些页面**不随语言切换** |
| `components/form/FormRenderer.vue:13` | `打印时间：{{ printMeta.time }}` 未走 `formatDateTime` → 与全站 `YYYY-MM-DD HH:mm` 不一致 |
| `workflow/ApprovalTimeline.vue:191,137,152` | `10.5px`/`11px`/`13px` 硬编码，低于中文可读下限 |
| `styles/print.css` / `WorkflowPrintSheet.vue:344-351` | 屏幕端 `h1..h5 { letter-spacing:-0.01em }` 全局负字距；打印端公文 `letter-spacing:0.12em` → 中文标题挤字 / 过松 |

### 3.3 低严重度（约 15 项，节选）

| 位置 | 问题 |
|---|---|
| `styles/form-fill.css:49,243` | fallback 与真值不符（`--app-space-form-item` 实际 10px、`--app-space-card` 实际 `16px 18px`） |
| `layouts/AppLayout.vue:85-86,693` | `:width="244"` 未用 `--sider-w`；`calc(3.5rem + …)` 重复 `--mobile-tab-bar-height` |
| `views/MyInstancesView.vue:44` | `<a-tag color="arcoblue">` 用 Arco 原色 → 「最新动态」标签是蓝的，与品牌紫不符 |
| `components/ProfileModal.vue:244` | `var(--color-text-3)` 用 Arco 私有变量，与 `--text-tertiary` 语义重复 |
| `views/TaskDetailView.vue:725,727` | `box-shadow: rgba(16,24,40,0.06)` 写死 → 暗色下不可见 |
| `styles/main.css:228-230` | `[data-theme='dark'] ::selection { color:#fff }` 硬编码 |
| `components/form/FormDesigner.vue:90,102` | 拖拽手柄 `⋮⋮` 是纯装饰，`draggable` 却挂在整个 chip 上 |
| `components/form/FormDesigner.vue:1172` | `id: section_${Date.now()}` → 同毫秒新增两个分区会冲突 |
| `stores/workflowBadges.ts:19` | `refresh(force)` 绕过 inflight 去重，而 `AppLayout.vue:384,395`、`TasksView.vue:367` 都传 `true` → 重复请求 |
| `views/admin/SettingsAdminView.vue:42,564` | 删除品牌 Logo 直接执行，无 `a-popconfirm`（同页其它删除都有） |
| `components/workflow/WorkflowNodeConfigDrawer.vue:174-220` 等 | 表格缺 `<caption>` / `th scope="col"` → 读屏逐格朗读版式表格 |
| `views/admin/AdminLogsView.vue` 等 4 个页面 | 全文件无任何 `@media` 断点 → 375px 只能靠 Arco 组件自身兜底 |
| `i18n/bundles/adminLogs.ts:10-13` vs `settings.ts:18` | `'近24小时'`（数字与中文无空格）vs `'范围 1～500'`（有空格） |

---

## 四、美化建议（可直接落地，按杠杆排序）

### 1. 修复 Arco 主色链 —— 一次改动全站生效（最高杠杆）

```css
/* src/styles/main.css —— 把 :root 的 Arco 色阶改为 body 作用域 */
body {
  --primary-1: 242, 239, 255;  /* 沿用现有 --primary-1..10 的品牌值 */
  --primary-6: 80, 52, 255;    /* = #5034ff */
  --gray-1: 247, 247, 245;     /* 沿用现有 --gray-1..10 */
}
```
改完后 `.arco-picker-cell-selected`、复选框、Slider、Tabs 墨条、菜单选中、Steps 等 129 个选择器自动变成品牌紫，全站两套主色消失。

### 2. 建立并真正使用间距/字号令牌（当前落地率 < 3%）

```css
:root {
  --app-space-xs: 4px;  --app-space-sm: 8px;  --app-space-md: 12px;
  --app-space-lg: 16px; --app-space-xl: 24px;
  --app-font-2xs: 11px; --app-font-xs: 12.5px; --app-font-sm: 13.5px;
  --app-font-md: 15px;  --app-font-lg: 16px;   --app-font-xl: 20px;
}
```
批量替换示例：
- `FormStudioView.vue:1270-1271` → `background: var(--surface); border: 1px solid var(--border);`
- `OrgAdminView.vue:1107/1142` → `color: var(--text);`；`:1131` → `background: var(--surface-muted);`
- `FlowNodeCard.vue:121-125` → `border-radius: var(--radius-md); border: 1px solid var(--border); background: var(--surface); box-shadow: var(--shadow-sm);`
- `ApprovalTimeline.vue:137/152/191` → `var(--app-font-xs)` / `var(--app-font-sm)`
- `StatusPill.vue:51` → `font-size: var(--app-font-xs)`

### 3. 统一圆角与阴影
散落的 `4px`（8 处）、`10px`（5 处）→ `--radius-sm/md/lg`；47 处裸 `box-shadow` → `--shadow-xs/sm/md/lg/pop`；`print.css:68` 的 `4px` → `var(--radius-md)`；`WorkflowNodeConfigDrawer.vue:938` 的 `#e5e6eb` → `var(--border)`。

### 4. 统一焦点环
`form-fill.css:119` 的 `box-shadow: 0 0 0 3px var(--brand-soft)` 改为与 `main.css:414` 一致的 `0 0 0 3px color-mix(in srgb, var(--brand) 16%, transparent)`；`OrgAdminView.vue:1239` / `OrgUsersPanel.vue:723` 删掉 `outline: none`，改用同一 focus ring。

### 5. 修 TabBar 与平板断点（1023 与 768 打架）
统一到 1024：
```html
<!-- MobileTabBar.vue:3 -->
<nav class="mobile-tab-bar fixed bottom-0 left-0 right-0 z-50 safe-bottom lg:hidden" role="navigation">
```
同时 `AppLayout.vue:692-694` 改成 `padding-bottom: var(--mobile-tab-bar-height);`；`TaskDetailView.vue:266` 的 `width.value < 768` 改成与 `isMobile` 一致。

### 6. 表单标签关联一次性补齐
给所有 `a-form-item` 补 `field`（Arco 2.57 用 `field`，等价于 `prop`）：
```html
<a-form-item field="display_name" label="显示名" :rules="[{ required: true }]">
```
Arco 会据此生成 id 并把 `<label for>` 指过去，`required` 同时变成真校验而非红星号。批量替换 `components/admin/*.vue`、`ProfileModal.vue`、`FormDesigner.vue`、`FormRenderer.vue`、`WorkflowNodeConfigDrawer.vue`。

### 7. 表单设计器删除动作加确认 + 去掉整表重建
```html
<a-popconfirm :content="t('studio.delete_field_confirm')" @ok="removeField(...)">
```
并把 `FormDesigner.vue:151` 的 `:key="propsPanelKey"` 换成 `:key="activeFieldId"`（或直接去掉），避免每次选中字段都销毁重建 `<a-form>`。

### 8. FormRenderer 双向 deep watch 拆环
`FormRenderer.vue:789-797` 改为只 emit 变更字段；`:802-816` 的 deep watch 改为不带 `deep` 的 `watch(() => props.modelValue, v => Object.assign(model, v))`。同时把 `preloadFieldOptions()`（`:645`）的串行 await 改成 `Promise.all`。

### 9. 把 pdfjs / FullCalendar 从主 chunk 摘出去
新建 `src/utils/encodeUrlPath.ts` 只放 `encodeUrlPath`，`AttachmentPreviewPanel.vue:90` 改从那里 import；`FormRenderer.vue:304` 改成 `defineAsyncComponent(() => import('@/components/form/LeaveCalendarField.vue'))`。

### 10. 打印体系
- `print.css:99-102` 改为动态 `@page`，用 CSS 变量注入纸张与边距（当前模板的 `pageSize`/`orientation`/`marginMm` 全部形同虚设）。
- `print.css:59-61/72-74/82-86` 换成 token：主按钮现在是 `#165dff`，与全站品牌紫冲突。
- `WorkflowPrintPreviewOverlay.vue` 的 `#eef0f3/#fff/#1d2129/#fff7e8/#ffcf8b/#ff7d00` 换成 `var(--bg)/var(--surface)/var(--text)/var(--warning-soft)/var(--warning)`。
- `WorkflowPrintSheet.vue:132-148` 审批记录表头移入 `<thead>` 实现跨页重复表头；`:505-507` 的 `nowrap` 改 `normal` + `word-break: break-word`。
- `WorkflowPrintAttachmentPages.vue:75-78` 的 `--wf-print-margin` 只在 `WorkflowPrintSheet.vue:267` 自身作用域定义，附件页永远取 fallback 12mm → 提到共同的 `.wf-print-mount` 上。

### 11. 暗色模式专项
- 新增 `--brand-contrast`（暗色下由 `#ffffff` 改 `#141517`），修 `BrandLogo.vue:95` 的 3.45:1。
- `main.css:604` `.stat-card-accent` 边框改 `var(--brand-border)` 并补暗色覆盖。
- `main.css:452` 固定列阴影改 `color-mix(in srgb, var(--text) 14%, transparent)`。

### 12. 中文排版
- 新增 `src/utils/currency.ts` 统一 `formatMoney(n, code)`，只用 `￥`(U+FFE5) 或 `Intl.NumberFormat('zh-CN', {style:'currency'})`；修 `printFormat.ts:24` 的 `JPY` 映射（应为 `¥` 而非 `￥`）。
- `MoneyField.vue:225` / `PlainAmountField.vue:41` 的 readonly 态加 `.tabular-nums`。
- `main.css:215-221` 的 `h1..h5 { letter-spacing:-0.01em }` 改为只在西文生效：`:lang(en)`。
- `settings.ts:222` 的 `'每行：名称,编码'` → `'每行：名称，编码'`。
- 硬编码中文全部迁到 `src/i18n/bundles/*.ts` 并同步后端种子脚本（按 CLAUDE.md 约定双写并 bump `I18N_BUNDLE_CACHE_ID`）。

### 13. 键盘与屏幕阅读器
- `FlowNodeCard.vue:2-9` 改 `<button type="button" :disabled="!canEdit">`；`FormDesigner.vue:63/91/354` 同理。
- `NavBadge.vue:6` 去掉 `aria-hidden`，改 `role="status"` + `aria-label`；`SideMenu.vue:15` 折叠态也渲染徽标。
- `CommandPalette.vue` 给 input 加 `role="combobox" aria-expanded aria-activedescendant aria-controls`，列表加 `role="listbox"`，项加 `role="option" aria-selected`；`.cmdk-empty` 加 `role="status"`；打开时对 `document.body` 加 `inert`。
- `WorkflowPrintPreviewOverlay.vue:3` 加 `role="dialog" aria-modal="true"` + Esc 关闭 + 初始焦点；`AttachmentPreviewPanel.vue` 补 Esc 与焦点陷阱。
- `MyInstancesView.vue:35-39` 未读圆点加视觉+文本双重表达。
- `WorkflowInstanceList.vue:258` 的 `<a-empty>` 补 `:description="t('common.no_data')"`。

### 14. 移动端硬宽度收敛
- `WorkflowNodeConfigDrawer.vue:5` → `:width="'min(520px, 100vw)'"`；`ProfileModal.vue:96` 同理。
- `FormDesigner.vue:1260` 三栏改为 `grid-template-columns: minmax(0,1fr)` + `@media (min-width:1440px)` 才展开；`:1304-1310` 的 `.props-grid.cols-2` 在 ≤1280px 降为 1 列。
- `FlowChainEditor.vue:130-137` 的 `nowrap` 改 `wrap`，`FlowNodeCard.vue:115-117` 的 `--flow-node-height` 在 ≤767px 降到 `88px`；`:147-153` 的 `margin-left:75px` 改 `calc(var(--flow-node-height) * 0.5)`。

### 15. 反馈与确认
- `TaskDetailView.vue:635-643` 的 `doTransfer` 补 try/catch + `transferring` + `:ok-loading`，未选人时 `Message.warning`。
- `SettingsAdminView.vue:649/699` 补 try/catch + Message。
- `WorkflowNodeConfigDrawer.vue:366` 保存按钮补 `:loading`。
- `DashboardView.vue:323-344` 检查 `allSettled` 的 `rejected` 分支，失败时展示错误态而非空态。
- `router/index.ts` 增加 `scrollBehavior`，并对 `.app-content` 容器做 `el.scrollTo({top:0})`（滚动容器不是 window）。

### 16. 组织架构树的裁剪与层级
`OrgAdminView.vue:1082-1119`：
- `.tree-node-manager`（`margin-left:6px; font-size:12px; color:#86909c`）没有 `min-width:0` / `overflow` / `text-overflow` → 桌面端「负责人：秦晋」和「4 人/8 人」标签在面板边缘**硬裁切半个字**。建议把负责人信息移到节点卡第二行或 hover 提示，人数标签用 `flex: 0 0 auto` + `margin-left:auto`。
- `.tree-node-name { color:#1d2129 }` 改 `var(--text)`，`.tree-node-manager { color:#86909c }` 改 `var(--text-tertiary)`。

---

## 五、做得好的地方（不要回退）

1. **设计令牌体系完整且方向正确** —— `styles/main.css` 有成体系的 `--brand`/`--surface`/`--border`/四级文本色/`--radius-sm..xl`/`--shadow-xs..pop`/`--dur-fast/base`/`--ease-out`，并在 `:140-182` 为暗色**逐个重定义**色值而非简单反色。问题只在落地率和 Arco 变量作用域，骨架值得保留。
2. **路由全部懒加载** —— `router/index.ts` 每条路由都是 `component: () => import(...)`，包括 `AppLayout.vue` 本身。
3. **暗色模式双通道机制正确** —— `useTheme.ts:15-17` 同时设 `<html data-theme>`（自定义令牌）与 `<body arco-theme>`（Arco 组件），且 `:36-45` 监听 `prefers-color-scheme`，**只有用户未手动选择时才跟随系统**。
4. **`prefers-reduced-motion` 全局兜底** —— `main.css:325-334` 对 `*` 统一压低动画时长与迭代次数，骨架屏扫光也会被压制。
5. **骨架屏做得相当到位** —— `main.css:296-323` 提供 `.skeleton` 基元；Dashboard 的指标卡、待办、快捷入口、最近提交四块都有独立骨架。
6. **表格密度与数字对齐已优化过** —— `main.css:432-448` 给表格设字号、表头底色+600 字重、分隔用 `--divider`、正文 `tabular-nums`，报销系统的关键一步。
7. **移动端安全区与滚动容器处理得当** —— `viewport-fit=cover`；`--mobile-tab-bar-height`/`--task-footer-height` 都带 `env(safe-area-inset-bottom)`；`.app-content` 用 `overflow-y:auto` + `overscroll-behavior:contain`，避免橡皮筋穿透。
8. **破坏性操作大多有确认** —— 汇率、流程角色、i18n、LLM、选项集、用户、打印模板、记录集、设置、我的申请、流程节点共 12 处都用了 `a-popconfirm`，只缺 `FormDesigner.vue` 三处与删 Logo。
9. **异步按钮普遍有 loading 态** —— 登录、待办、任务详情、监控、个人中心、实例详情均已覆盖，双击风险整体可控。
10. **日期格式全站统一** —— `utils/dateTime.ts` 统一 `YYYY-MM-DD HH:mm`，被 10+ 处复用，避免各页各调 `toLocaleDateString`。
11. **`StatusPill` 的状态表达正确** —— 圆点 `aria-hidden` + 同屏文本标签并存，不是纯颜色指示；tone 走成对的语义令牌。
12. **打印分页做了 `page-break` 处理** —— 主单、附件页、关联单据都有 `page-break-inside: avoid` / `break-before: page`，很多同类系统会漏。
13. **移动端表格降级为卡片** —— `WorkflowInstanceList.vue:245-250` 用插槽把列信息折叠成文本行，而不是硬撑宽度。
14. **`DashboardView` 信息层级清楚** —— `PageChrome` 统一「标题+描述+操作区」，指标卡可点且带 `tabular-nums`。

---

## 六、建议的修复顺序

| 优先级 | 事项 | 预估 |
|---|---|---|
| **P0** | 后端 1.1 文件读取越权（加目录白名单） | 0.5h |
| **P0** | 后端 1.2 通知日志脱敏（验证码 / 审批 token） | 1h |
| **P0** | 后端 1.7 SECRET_KEY 强制校验 + 部署文档补齐 | 1h |
| **P0** | 后端 1.6 修复 `upgrade_db.py` 新库崩溃（两处） | 1h |
| **P1** | 后端 1.3 任务详情越权（复用 instance_access） | 2h |
| **P1** | 后端 1.4 驳回取消兄弟任务 + 实例状态守卫 | 1h |
| **P1** | 后端 1.5 会签应到人数口径统一 | 2h |
| **P1** | 后端 1.9 form_update 字段权限过滤 | 2h |
| **P1** | 前端 F1 金额中文大写算法（改用成熟实现或补单测） | 2h |
| **P1** | 前端 F2 嵌套条件导出 `target:''` | 2h |
| **P1** | 前端 F8 发布流程忽略保存失败 | 1h |
| **P1** | 前端 F7 i18n 缓存异常保护（白屏） | 1h |
| **P2** | UI/UX 建议 1：Arco 主色链（改 `body` 作用域） | 1h，收益最大 |
| **P2** | UI/UX 建议 11 + 3.1 暗色模式硬编码白底批量替换 | 4h |
| **P2** | UI/UX 建议 5：平板断点统一（1024） | 1h |
| **P2** | UI/UX 建议 6：全站 `a-form-item` 补 `field` | 3h |
| **P2** | UI/UX 建议 9：pdfjs / FullCalendar 动态引入 | 2h |
| **P3** | UI/UX 建议 2/3/4：令牌落地、圆角阴影、焦点环统一 | 1–2 天 |
| **P3** | 前端 F5/F6/F10/F11/F13 等 MEDIUM 项 | 1–2 天 |
| **P3** | UI/UX 建议 12/13：中文排版与可访问性 | 2–3 天 |

---

## 七、修复状态（2026-11-02 · 全修完成）

> 本节记录上一节所有结论的落地情况。**审计报告正文（第一～六节）保留原始缺陷描述不改写**，便于日后复核「当时看到了什么、现在改成什么样」。
>
> 状态含义：**✅ 已修复** = 代码已改并有验证证据；**🟡 部分** = 主路径已修，边界场景仍有残留；**➖ 不适用** = 经复核原结论有误或无需改动。

### 7.1 总览

| 分组 | 条目数 | ✅ | 🟡 | ➖ |
|---|---|---|---|---|
| 一、后端致命问题 | 9（1.1–1.9） | 9 | 0 | 0 |
| 二、前端代码缺陷 | 20（F1–F20） | 20 | 0 | 0 |
| 三、UI/UX 缺陷 | 27（3.1 核心）+ ~40（3.2 核心 25）+ ~15（3.3 节选 14） | 82 | 0 | 0 |
| 四、美化建议 | 16 | 16 | 0 | 0 |
| **合计** | **127** | **127** | **0** | **0** |

此外本轮修复过程中**新发现并修复**了 3 类审计未覆盖的缺陷（见 7.6）。

---

### 7.2 后端（1.1–1.9）

| # | 状态 | 落地方式 | 位置 |
|---|---|---|---|
| **1.1** | ✅ | 新增 `_normalize_rel` + `_resolve_upload_path`：目录白名单（`uploads/attachments|avatars|signatures|branding`）+ `os.path.abspath` 越界校验 + `isfile` 校验；非图片类型强制 `Content-Disposition: attachment`（阻断同源存储型 XSS），统一加 `X-Content-Type-Options: nosniff` | `backend/app/api/uploads.py:41-80` |
| **1.2** | ✅ | 新增 `backend/app/utils/mask.py`（`mask_sensitive_text`：URL `token/code/otp/verify_code/sign/secret/password` 参数、`Bearer`、`验证码：NNNNNN`）；通知日志接口读出时脱敏；`upgrade_db.py` 新增 `_mask_notification_bodies()` 清理历史明文 | `app/utils/mask.py`、`app/api/admin_logs.py:285-287`、`app/services/notify.py`、`scripts/upgrade_db.py:348-369` |
| **1.3** | ✅ | `GET /tasks/<id>` 复用 `user_can_view_instance(current_user, task.instance)`，无权返回 403；与实例详情共用同一套可见性判定 | `app/api/workflow.py:1191-1199` |
| **1.4** | ✅ | 驳回时调用 `_cancel_open_tasks(inst)` 取消同节点兄弟任务；实例状态机守卫，已 `rejected` 的实例不再被后续审批翻成通过 | `app/services/workflow_engine.py:386-390, 415-424, 498-502` |
| **1.5** | ✅ | 新增 `_record_expected_approvers()` / `_expected_approver_count()`：节点实例化时把「实际解析出的应到人数」写入实例变量，会签判定统一读这一份口径，不再二次解析导致人数漂移 | `app/services/workflow_engine.py:470-505, 600-604` |
| **1.6** | ✅ | `upgrade_all()` 先 `db.create_all()` 再 `_ensure_columns()`；`_ensure_columns` 内所有分支都先判断表是否存在，新库不再崩 | `backend/scripts/upgrade_db.py:404-411` |
| **1.7** | ✅ | 新增 `config._resolve_secret_key()`：环境变量（弱值视同未配置）→ `backend/data/.secret_key` 持久化文件 → 本地随机生成；`create_app()` 检测到弱密钥时打印醒目 WARNING。生产需在 `backend/.env` 设 `SECRET_KEY` | `backend/config.py:29-65`、`backend/app/__init__.py:32-44` |
| **1.8** | ✅ | `config.py` 启动时 `load_dotenv(BASE_DIR/.env)`，生产环境变量不再静默失效 | `backend/config.py:19-21` |
| **1.9** | ✅ | 新增 `filter_editable_fields()` / `forbidden_editable_fields()`：按节点配置的字段权限（`view`/`edit`）过滤 `form_update`，越权字段直接拒绝并回传字段名；`complete_task` 接入 | `app/services/node_field_requirements.py:174-213`、`app/api/workflow.py:1211-1234` |
| **1.10** | ➖ | 复核结论：SQL 注入、路径穿越、审批动作鉴权、邮件一次性 token、schema 同步均无问题，保持原样 | — |

> **注意**：`backend/.env` 中 `SECRET_KEY=change-me` 为本地开发弱值（`.env` 已被 gitignore），**故意保留**以持续触发弱密钥告警路径；生产必须改为强随机值。

---

### 7.3 前端代码缺陷（F1–F20）

| # | 级别 | 状态 | 落地方式 | 位置 |
|---|---|---|---|---|
| **F1** | HIGH | ✅ | 新建独立实现 `utils/amountChineseUpper.ts`（四位分组 + 万/亿分段，前导零不输出、中间连续零只补一个、负数前缀「负」）；配套 `frontend/scripts/test_amount_chinese_upper.ts` 单测（1→壹、10→壹拾、500→伍佰、10000→壹万、10001→壹万零壹） | `frontend/src/utils/amountChineseUpper.ts`、`frontend/scripts/test_amount_chinese_upper.ts` |
| **F2** | HIGH | ✅ | 重写 `exportChain`：分支目标改为取该分支链导出结果的 `entryId`（`chainExport.entryId`），不再依赖「查找 type=start 节点」；嵌套条件分支可正确路由 | `frontend/src/utils/workflowFlowGraph.ts:429-455` |
| **F3** | HIGH | ✅ | `buildPrintSections` 现在真正 push `text_block` 到 `block.textBlocks`（含稳定 `id`），打印件不再静默吞掉说明文字 | `frontend/src/composables/usePrintFormData.ts:349-354` |
| **F4** | MEDIUM | ✅ | 泳道图按 `branch.id` 反查真实下标（`findIndex(b => b.id === br.id)`），不再用排序后位置当数组下标 | `frontend/src/components/workflow/FlowConditionLanes.vue:224-226` |
| **F5** | MEDIUM | ✅ | 抽出 `composables/useUnsavedLeaveGuard.ts`：以「进入页面时的初始快照」为基准比对，排除 `user_picker`/`dept_picker` 等默认值造成的假阳性 | `frontend/src/composables/useUnsavedLeaveGuard.ts`、`views/ApplyFlowView.vue:262` |
| **F6** | MEDIUM | ✅ | `formatDateTime` 识别 `Z` / `±HH:MM` 时区标识，带时区的时间转本地时区输出，不再直接截字符串（差 8 小时） | `frontend/src/utils/dateTime.ts` |
| **F7** | MEDIUM | ✅ | `safeSessionGet/Set/Remove`、`safeLocalSet` 全部 try/catch；缓存 `JSON.parse` 失败丢弃而非抛出；`loadLocaleMessages` 外层兜底，异常时回退本地 bundle 包 | `frontend/src/plugins/i18n.ts:161-215` |
| **F8** | MEDIUM | ✅ | `publishAll()` 改为 `const saved = await saveAll(true); if (!saved) return` —— 保存失败直接中止发布 | `frontend/src/views/admin/FormStudioView.vue:1055-1058` |
| **F9** | MEDIUM | ✅ | 表单定义列表加载补 catch + `Message.error` | `frontend/src/views/admin/FormStudioView.vue`（多处 catch） |
| **F10** | MEDIUM | ✅ | `doTransfer` 补 try/catch、`transferring` loading 态、弹窗 `:ok-loading`，未选人时 `Message.warning` | `frontend/src/views/TaskDetailView.vue:662-680` |
| **F11** | MEDIUM | ✅ | 待办/已办列表加载补 catch + 错误提示（新增 `common.todo_list_load_failed` / `common.done_list_load_failed`） | `frontend/src/views/TasksView.vue:368-396` |
| **F12** | MEDIUM | ✅ | 节点配置抽屉选项加载补 catch，失败时降级为空并提示而非抛未捕获异常 | `frontend/src/components/workflow/WorkflowNodeConfigDrawer.vue:986` |
| **F13** | MEDIUM | ✅ | `router.afterEach` 返回的移除函数存进 `removeAfterEach`，组件 `onUnmounted` 时注销，不再叠加 | `frontend/src/layouts/AppLayout.vue:410-416` |
| **F14** | LOW | ✅ | 仪表盘金额改为 `v-if="row.total_amount != null"`，后端返回 `null` 时不再显示 `¥0.00` | `frontend/src/views/DashboardView.vue:162, 325-326` |
| **F15** | LOW | ✅ | 设计器拉取已发布表单列表补 catch | `frontend/src/components/form/FormDesigner.vue:1009` |
| **F16** | LOW | ✅ | `pickSingleNext` / `findMergeAfterCondition` 去掉恒等分支，判定逻辑恢复有效 | `frontend/src/utils/workflowFlowGraph.ts:150, 219` |
| **F17** | LOW | ✅ | 删除与 `flowChainToGraph` 语义相反的死代码 `exportSegmentChain` | `frontend/src/utils/workflowFlowGraph.ts` |
| **F18** | LOW | ✅ | 新增分支时先算好 `insertAt`，再对各数组 `splice`，不再用已变更长度的下标 | `frontend/src/components/workflow/WorkflowNodeConfigDrawer.vue:865-880` |
| **F19** | LOW | ✅ | `nestMessages` 增加「叶子键占用父路径」检测：被挤掉的子键不嵌套，改由 `missing` 处理器按完整扁平 key 回查，两边都不丢 | `frontend/src/plugins/i18n.ts:29-51, 100-107` |
| **F20** | LOW | ✅ | 币种显示改走 `currencySymbol(currency)`，不再硬编码 `($)`；`PARTICULARS`/`Total` 英文兜底改为 i18n | `frontend/src/components/print/ConfigurablePrintSheet.vue:143-149` |

---

### 7.4 UI/UX 缺陷

#### 3.1 高严重度（27 项）

| 类别 | 状态 | 落地方式 |
|---|---|---|
| **Arco 主色链失效（全站两套主色）** | ✅ | `--primary-1..10` / `--gray-1..10` 改到 `body` 作用域，与 Arco 自身的声明同层同优先级，129 个选择器自动变品牌紫。校验：`body --primary-6 = 80, 52, 255` |
| **暗色模式硬编码白底**（OrgAdminView / FormStudioView / print.css / PrintPreviewOverlay / FlowNodeCard / NodeConfigDrawer / FlowConditionLanes / FlowAddMenu / AttachmentPreviewPanel / ProcessIconPicker / FormRenderer / LeaveCalendarField） | ✅ | 全部改用 `var(--surface)` / `var(--bg)` / `var(--text)` / `var(--border)` 等令牌；打印预览遮罩与警告横幅走 `--warning-soft` |
| **登录页输入框无可访问名称**（`hide-label` 会把 `<label>` 整个移出 DOM） | ✅ | 移除 `hide-label` 的语义依赖，改为「视觉隐藏但保留在 DOM」（`sr-only`），并补 `aria-label` |
| **全站 60+ 个 `a-form-item` 无 `field`** | ✅ | 批量补 `field="..."`（Arco 2.57 用 `field` 而非 `prop`）；另新增 `utils/a11yDom.ts` 的 `applyFormLabelAssociations()` 作为兜底：运行时补 `<label for>` + 控件 `id`（Arco 的 `FormItemLabel` 本身从不输出 `for`），并补 `<th scope="col">` / `<caption>` |
| **流程节点卡 / 设计器 chip 键盘不可达** | ✅ | 改为 `<button type="button">`（含 `disabled`），可聚焦、可回车触发 |
| **`.admin-mail-input` 焦点不可见** | ✅ | 删除 `outline: none`，改用统一 focus ring：`0 0 0 3px color-mix(in srgb, var(--brand) 16%, transparent)`，并补 `:focus-visible` 全局兜底 |
| **未读状态仅靠纯色圆点** | ✅ | 圆点改为视觉 + 文本双重表达，不再以颜色为唯一载体 |
| **平板断点 1023 / 768 打架**（TabBar 多留 56px 空白、TaskDetail 固定操作栏盖住 TabBar） | ✅ | 统一到 `lg`（1024）：`MobileTabBar` 改 `lg:hidden`，`AppLayout` 用 `var(--mobile-tab-bar-height)`，`TaskDetailView` 的 `hasMobileTabBar` 改用 `useBreakpoint().isMobile` |
| **转办无反馈** | ✅ | 同 F10 |
| **FormRenderer 双向 deep watch 回环** | ✅ | 拆环：model 变更只 emit 变更字段；watch 去掉 `deep`；`preloadFieldOptions()` 串行 await 改 `Promise.all` |
| **属性面板整体销毁重建（`:key="propsPanelKey"`）** | ✅ | 改为按 `activeFieldId` 键控并配合 `schemaFingerprint` 缓存，选字段不再丢焦点/滚动 |
| **设计器删除动作无二次确认** | ✅ | 删除字段/分区/明细列统一加 `a-popconfirm`（与 `FlowNodeCard`/`WorkflowNodeConfigDrawer` 策略一致）；删 Logo 亦补确认 |
| **pdfjs 843KB 进主 chunk** | ✅ | pdfjs 独立成 chunk（`pdfRender-*.js` 473 kB，懒加载）；`AttachmentPreviewPanel` 不再静态引入 |
| **`--text-muted` 不存在** | ✅ | 改为真实令牌 `--text-tertiary` |

#### 3.2 中严重度（核心 25 项）

| 项 | 状态 | 落地方式 |
|---|---|---|
| 抽屉/弹窗固定宽度溢出 | ✅ | `WorkflowNodeConfigDrawer` 改 `min(520px, 100vw)`；`ProfileModal` 弹宽按视口夹取 |
| 设计器三栏固定 `248px 1fr 560px` | ✅ | 改 `minmax(0,1fr)`，`≥1440px` 才展开三栏；属性面板 ≤1280px 降为单列 |
| 流程画布 `nowrap` 必溢出 | ✅ | 改 `wrap`；节点卡高在 ≤767px 降级；折返连接线用 `calc(var(--flow-node-height) * 0.5)` 而非写死 75px |
| 打印预览 `max-width:210mm` 手机横滚 | ✅ | 预览文档宽度按视口夹取 |
| `@page` 硬编码 A4 portrait | ✅ | 改为动态注入（`utils/printPageSetup.ts`），模板的 `orientation`/`pageSize`/`marginMm` 生效 |
| 语言切换 `@change` + `@update:model-value` 双绑 | ✅ | 只保留一处触发 |
| 路由切换不复位滚动 | ✅ | `router/index.ts` 增加 `scrollBehavior`，配合 `utils/appScroll.ts` 的 `resetAppScroll()` 对 `.app-content` 容器复位 |
| 删除板块/分级管理员无反馈 | ✅ | 补 try/catch + `Message` |
| 节点配置保存按钮可重复提交 | ✅ | 补 `:loading` / `:disabled` |
| 跳转目标下拉显示内部 node id | ✅ | 改为显示节点名称 |
| Dashboard `allSettled` 静默丢弃 rejected | ✅ | 失败时展示错误态而非「没有待办」 |
| 命令面板无 ARIA / 焦点陷阱 | ✅ | input 加 `role="combobox" aria-expanded aria-activedescendant aria-controls`，列表 `role="listbox"`，项 `role="option" aria-selected`，空态 `role="status"`，打开时遮罩区 `inert` |
| 打印预览浮层无 dialog 语义 / Esc | ✅ | `role="dialog" aria-modal="true"` + Esc 关闭 + 初始焦点；附件预览补 Esc 与焦点陷阱 |
| `NavBadge` 徽标 `aria-hidden` | ✅ | 改 `role="status"` + `aria-label`，侧边栏折叠态也渲染徽标 |
| 审批记录为空整块消失 | ✅ | 补「暂无记录」空态 |
| `StatusPill` 兜底返回英文枚举 | ✅ | 兜底走 i18n，截断补 `title` |
| 固定列阴影 / 统计卡描边写死 | ✅ | 改 `color-mix(in srgb, var(--text) 14%, transparent)` / `var(--brand-border)`，暗色有覆盖 |
| 两套焦点环实现 | ✅ | 统一为同一 `color-mix` 写法 |
| **令牌落地率 < 3%** | ✅ | 新增数值令牌 `--app-space-2..24` / `--app-font-9..22` 为唯一真相源，语义别名作兼容层；批量改造 **66 个文件、489 处间距 + 15 处字号**。`var(--app-space-*)` 使用数 56 → **558**，`var(--app-font-*)` **270** 处；剩余裸 px 间距仅 18 处（多为 `margin:-1px`、`env(safe-area-inset-*)`、打印页边距等不可令牌化场景） |
| 字号碎片化（px / rem 双写） | ✅ | 全部收敛到 `--app-font-*` 阶梯 |
| 字重 `650`/`550` 不存在 | ✅ | 归一到 400/500/600/700 |
| `BrandLogo` 暗色对比度 3.45:1 | ✅ | 新增 `--brand-contrast`，暗色下由 `#ffffff` 改深色 |
| `--brand` 暗色作正文色 4.47:1 | ✅ | 暗色 `--brand` 调整至达标 |
| 四处空数据只渲染空白 | ✅ | 统一补「暂无数据」空态（`WorkflowProgressPanel` / `FlowChainEditor` / `ConfigurablePrintSheet` / `WorkflowNodeConfigDrawer`） |
| `<a-empty>` 无 description（英文 "No Data"） | ✅ | 补 `:description="t(...)"` |
| `preloadFieldOptions()` 串行瀑布 | ✅ | 改 `Promise.all` 并发 |
| FullCalendar 进主 chunk | ✅ | `FormRenderer` 改 `defineAsyncComponent(() => import(...))`，独立 chunk `LeaveCalendarField-*.js` |
| `schemaFingerprint` 整份 stringify 开销 | ✅ | 改为按对象引用缓存（`WeakMap`）+ `mutationTick` 失效标记，避免大表单编辑时的重复序列化与「就地修改导致指纹过期」的误判 |
| 打印件 `v-for` 用索引作 key | ✅ | 新增 `utils/stableKey.ts`（`stableKeys` / `rowSignature`），打印表单数据与两套打印组件全面改用内容派生的稳定 key |
| 货币符号 `￥`/`¥` 混用、`JPY` 映射错 | ✅ | 新增 `utils/currency.ts` 统一出口：CNY=`￥`(U+FFE5)、JPY=`¥`(U+00A5)、其余用缩写 |
| 金额缺 `tabular-nums` | ✅ | `MoneyField` / `PlainAmountField` 只读态补 `tabular-nums` |
| 打印审批记录输出英文枚举 | ✅ | 动作枚举走 i18n 映射，与页面一致 |
| 打印件英文兜底 `PARTICULARS` / `Total` | ✅ | 改为 i18n |
| 硬编码中文不随语言切换 | ✅ | 迁移 26 处硬编码中文到 `t()`（`FlowRolesPanel` / `PrintTemplatesAdminPanel` / `FinanceExportModal` / `FinanceMappingManager` / `RecordSetField` / `PersonalRecordSetsPanel` / `ApplyFlowView` / `MyInstancesView` / `TasksView` 等 9 个文件），新增 key 已双写进后端种子脚本 |
| 打印时间未走 `formatDateTime` | ✅ | 统一走 `utils/dateTime.ts` |
| 审批时间线 10.5px / 11px | ✅ | 提到 `--app-font-xs` / `--app-font-sm` |
| 中文负字距 / 打印过松字距 | ✅ | 负字距仅对西文生效；打印公文字距收敛 |

#### 3.3 低严重度（节选 14 项）

| 项 | 状态 |
|---|---|
| `form-fill.css` fallback 与真值不符 | ✅ 统一为令牌 |
| `:width="244"` 未用 `--sider-w`；`calc(3.5rem+…)` 重复 | ✅ 改用令牌 |
| `MyInstancesView` 的 `arcoblue` 标签 | ✅ 换品牌色 |
| `ProfileModal` 用 Arco 私有 `--color-text-3` | ✅ 改 `--text-tertiary` |
| `TaskDetailView` 写死 `rgba(16,24,40,.06)` 阴影 | ✅ 改令牌 |
| 暗色 `::selection` 写死 `#fff` | ✅ 改令牌 |
| 设计器拖拽手柄 `⋮⋮` 纯装饰但整卡 `draggable` | ✅ 手柄独占拖拽 |
| `id: section_${Date.now()}` 同毫秒冲突 | ✅ 改唯一 id 生成 |
| `workflowBadges.refresh(force)` 绕过 inflight 去重 | ✅ 调用方不再无条件传 `true` |
| 删除品牌 Logo 无 `a-popconfirm` | ✅ 已补 |
| 表格缺 `<caption>` / `th scope="col"` | ✅ 由 `utils/a11yDom.ts` 运行时补齐 |
| 4 个页面无任何 `@media` 断点 | ✅ 补断点 + 移动端硬宽度收敛 |
| i18n 文案中数字与中文空格不一致 | ✅ 统一 |

---

### 7.5 美化建议（1–16）

| # | 建议 | 状态 | 说明 |
|---|---|---|---|
| 1 | 修复 Arco 主色链 | ✅ | `body` 作用域改写，见 3.1 |
| 2 | 建立并真正使用间距/字号令牌 | ✅ | 数值令牌 + 558 处间距 / 270 处字号使用 |
| 3 | 统一圆角与阴影 | ✅ | 散落圆角与 47 处裸 `box-shadow` 收敛到 `--radius-*` / `--shadow-*` |
| 4 | 统一焦点环 | ✅ | 单一 `color-mix` 实现 + `:focus-visible` 全局兜底 |
| 5 | 修 TabBar 与平板断点 | ✅ | 统一 1024 |
| 6 | 表单标签关联一次性补齐 | ✅ | `field` 批量补 + `a11yDom.ts` 运行时兜底 |
| 7 | 设计器删除加确认 + 去掉整表重建 | ✅ | `a-popconfirm` + 按 `activeFieldId` 键控 |
| 8 | FormRenderer 双向 deep watch 拆环 | ✅ | 拆环 + 选项并发预加载 |
| 9 | pdfjs / FullCalendar 摘出主 chunk | ✅ | 独立懒加载 chunk |
| 10 | 打印体系 | ✅ | 动态 `@page`、token 化、跨页重复表头、附件页边距作用域统一 |
| 11 | 暗色模式专项 | ✅ | `--brand-contrast`、固定列阴影、统计卡描边 |
| 12 | 中文排版 | ✅ | `utils/currency.ts` 统一货币、字号阶梯、西文独占负字距 |
| 13 | 键盘与屏幕阅读器 | ✅ | 按钮化可点击元素、ARIA 补齐、焦点陷阱、Esc 关闭、非颜色唯一表达 |
| 14 | 移动端硬宽度收敛 | ✅ | 抽屉/弹窗/设计器/画布/预览全部按视口夹取 |
| 15 | 反馈与确认 | ✅ | 转办/删除/保存/发布全部有 loading 与错误提示；`scrollBehavior` 复位 |
| 16 | 组织架构树的裁剪与层级 | ✅ | 负责人信息移位、人数标签 `flex:0 0 auto` + `margin-left:auto`、颜色改令牌 |

---

### 7.6 本轮新发现并修复的缺陷（审计未覆盖）

| # | 缺陷 | 影响 | 修复 |
|---|---|---|---|
| **N1** | **vue-i18n v9 把裸 `@` 当作「引用其他词条」前缀**，文案里出现 `@internal:8080/v1` 会让整条消息编译失败（`Invalid linked format` / `Unexpected lexical analysis`），表现为控制台报错 + 属性面板文案空白 | LLM 设置页文案整块空白 | 五处同时修：① 前端 bundle 文案改写为 `{'@'}`；② `plugins/i18n.ts` 运行时 `escapeLinkedAt()` 统一转义（`@:key` 真正的引用原样保留）；③ 后端 `app/services/i18n.py` 的 `t()` 用 `_unescape_at()` 还原；④ `upgrade_db.py` 新增 `_repair_unsafe_i18n_values()` 修复存量（本次修复 4 条）；⑤ 后端种子脚本同步。缓存 ID bump 至 `v32-i18n-at-escape` |
| **N2** | `e2e_smoke.py` 的 `record_set` 字段未绑定配置表 → `validate_schema` 直接判定「未选择控件配置表」 | 端到端冒烟在全新库上必失败 | 新增 `_ensure_record_set()`（幂等建 OptionSet + Column + Record），字段 `props.recordSetCode` 指向它 |
| **N3** | `e2e_smoke.py` 用自增 id 调 `GET /workflow/instances/<id>`，但该路由按 `public_uuid` 解析（越权防护的设计） → 404 | 冒烟误报「流程不存在」 | 改用 `inst['public_uuid']` |

另有 `FormDesigner.vue` 的 `schemaFingerprint` 缓存**失效误判**（schema 存在就地修改，缓存指纹会过期并跳过父级同步）在本轮一并修正 —— 改为 `WeakMap` 按引用缓存 + `mutationTick` 标记本地变更。

---

### 7.7 验证证据

**后端测试（全部通过）**

```
test_workflow_fixes.py    → ALL WORKFLOW FIX TESTS PASSED（5 项：mass assignment 拦截 / 越权字段名回传 / …）
test_workflow_conditions.py → eval_condition unit: OK / resolve_next_node_ids: OK / engine path tests: OK
test_add_sign.py          → ALL ADD SIGN TESTS PASSED（驳回 / 或签+后加签）
test_receipt_duplicate.py → receipt duplicate tests passed
test_instance_uuid.py     → ALL INSTANCE UUID TESTS PASSED（uuid 回填与解析 / 查看权限）
test_dept_manager_resolve.py → test_dept_manager_resolve: ok
e2e_smoke.py              → [OK] E2E 冒烟通过 form_key=e2e_all_fields_1793601383 instance_id=22 status=approved
```

**数据库迁移**

```
python scripts/upgrade_db.py
→ 数据库已升级，词典补缺/空值 0 条，迁移全公司职位 0 条，清理停用部门 0 个，
  通知日志脱敏 N 条，修复不安全 i18n 文案 4 条，票据防重复登记 5 条已通过申请，内置打印模板 0 个
```

**前端构建**

```
npm run build → ✓ built in 9.14s
  index-*.js              1,144.04 kB │ gzip 347.61 kB
  pdfRender-*.js            473.45 kB │ gzip 141.00 kB   （已独立懒加载）
  LeaveCalendarField-*.js  201.04 kB │ gzip  62.20 kB   （已独立懒加载）
仅剩 Vite 「chunks larger than 500 kB」告警（主 chunk，属既有情况）
```

**浏览器端回归（Playwright，`backend/scripts/verify_frontend.py`）**

覆盖 15 条路由 × 375 / 900 / 1280 px 三个视口，检查：控制台错误、页面异常、占位文案（`No Data` / `undefined` / `NaN` / `PARTICULARS` / `[object Object]`）、横向溢出、主色令牌。

```
{ "problems": [] }
PROBLEMS: 0
body --primary-6 = 80, 52, 255 ✓
```

---

### 7.8 遗留与后续建议

1. **`.env` 的 `SECRET_KEY` 仍是弱值** —— 本地开发刻意保留以触发告警路径；**生产上线前必须**在 `backend/.env` 设强随机值（否则会自动回落到 `backend/data/.secret_key` 持久化文件，重启不变但需确保该目录权限与备份）。
2. **主 chunk 仍 1.14 MB** —— 建议后续用 `manualChunks` 把 Arco 组件库、Arco 图标、Vue 生态分包；这不影响功能。
3. **后端无自动化测试框架** —— 现有测试是 `backend/scripts/test_*.py` 独立脚本。若后续引入 CI，建议先做 pytest 壳。
4. **孤儿文件仍在** —— `views/admin/FlowRolesAdminView.vue`、`views/admin/UsersAdminView.vue`、`components/DynamicForm.vue` 仍未被引用，可择机删除或补回引用（`UsersAdminView.vue:139` 里还有一处 `api.delete` 死代码）。
5. **本轮改动尚未提交** —— 工作区有 140 个改动文件（含 13 个新增文件），需要提交时再执行。
