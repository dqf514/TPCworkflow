# TPC 工作台 Windows 客户端



企业微信风格的审批桌面客户端，对接现有 TPCWorkflow 系统。



## 功能清单



- 账号密码 + 图形验证码登录，设备令牌静默续期

- 邮箱验证码登录（客户端免图形验证码）

- 左侧导航 + WebView2 详情（工作台、发起申请、我的申请、待办审批）

- SSE 实时推送 + Windows 桌面通知 + 托盘气泡

- 关闭窗口最小化到托盘（可设置）

- 开机自动启动（可设置）

- 单实例运行 + `tpcworkflow://` 深链接

- 按权限显示管理入口

- Web 嵌入模式 `?embed=desktop`（不影响浏览器访问）



## 程序图标



图标资源位于 `Assets/`：



- `app-icon.png` — 窗口左上角展示

- `app.ico` — 程序图标、任务栏与托盘（由 `scripts/build-icon.ps1` 从 PNG 生成）



修改图标后执行：



```powershell

.\scripts\build-icon.ps1

dotnet build -c Release

```



## 配置



首次配置可编辑 `appsettings.json`，登录后可在「设置」中修改：



```json

{

  "ServerBaseUrl": "https://wf.imcsh.com",

  "DeviceName": "Windows 工作台",

  "MinimizeToTray": true,

  "AutoStart": false,

  "EnableNotifications": true

}

```



用户偏好保存在 `%LocalAppData%\TPCWorkflow\preferences.json`。



## 构建与运行



```powershell

cd client

dotnet restore

dotnet build -c Release

dotnet run

```



## 打包发布（推荐）



**无需手动拷贝多个 DLL**，使用单文件自包含发布：



```powershell

cd client

.\publish.ps1

```



产物：



| 路径 | 说明 |

|------|------|

| `client/publish/win-x64/TPCWorkflow.Client.exe` | 单文件可执行程序 |

| `deploy/downloads/TPCWorkflow.Client.exe` | 供网页下载的安装包副本 |



说明：



- 采用 `PublishSingleFile` + `SelfContained`，用户只需一个 exe，无需单独拷贝依赖文件夹

- 仍需安装 [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)（Win11 通常已自带）

- 首次启动会解压内置运行时到临时目录，属正常现象



## 深链接



| 协议 | 说明 |

|------|------|

| `tpcworkflow://task/123` | 打开待办详情 |

| `tpcworkflow://instance/{uuid}` | 打开申请详情 |

| `tpcworkflow://open/apply` | 打开发起申请 |



## 网页下载



登录后点击右上角头像 → **下载 Windows 客户端**，从服务端 `deploy/downloads/TPCWorkflow.Client.exe` 下载。



部署前在服务器执行 `client/publish.ps1`（或本地发布后上传 exe）。



## 服务端要求



需部署后端 `/api/v1/client/download` 接口与前端头像菜单，并执行 `npm run build`。



## 上传命令（CMD 一行）



```cmd

tar -czf - -C "D:\AI\TPCWorkflow" "backend/app/api/client.py" "backend/app/services/client_download.py" "backend/config.py" "backend/scripts/seed_i18n_zh_cn.py" "backend/scripts/seed_i18n_en_us.py" "frontend/src/layouts/AppLayout.vue" "frontend/src/plugins/i18n.ts" "frontend/src/i18n/bundles/client.ts" "client/Assets" "client/scripts/build-icon.ps1" "client/publish.ps1" "client/TPCWorkflow.Client.csproj" "client/MainWindow.xaml" "client/LoginWindow.xaml" "client/README.md" "deploy/downloads/README.md" | ssh "david@10.1.40.108" "mkdir -p /tmp/tpcworkflow && tar -xzf - -C /tmp/tpcworkflow"

```



若已本地执行 `publish.ps1`，请额外上传 exe：



```cmd

tar -czf - -C "D:\AI\TPCWorkflow" "deploy/downloads/TPCWorkflow.Client.exe" | ssh "david@10.1.40.108" "mkdir -p /tmp/tpcworkflow && tar -xzf - -C /tmp/tpcworkflow"

```



服务器上：



```bash

# 合并代码后

cd /path/to/TPCWorkflow/frontend && npm run build

# 若未上传 exe，在服务器编译客户端：

cd ../client && pwsh ./publish.ps1

# 可选：同步 i18n

cd ../backend && .venv/bin/python scripts/seed_i18n_zh_cn.py

```


