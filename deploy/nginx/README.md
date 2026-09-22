# wf.imcsh.com 生产部署

## 架构

```
浏览器 / 客户端
      │
      ▼
  Nginx (wf.imcsh.com:443)
      ├── /api/*  ──► 10.1.40.109:5320  Flask 后端（新增）
      └── /*      ──► 10.1.40.109:5321  Web 前端（保持不变）
```

- **Web 页面**：仍走 `5321`，现有发布方式不变
- **桌面客户端**：请求 `https://wf.imcsh.com/api/v1/...`，由 Nginx 转到 `5320`
- **浏览器里的 API**：若前端请求同源 `/api/v1`，也会走 Nginx 到 `5320`（与 Vite 开发代理效果一致，通常更稳）

## 操作步骤

### 1. 确保后端在 5320 运行

```bash
# 在 10.1.40.109 上
curl -s http://127.0.0.1:5320/api/v1/health
```

### 2. 编辑 Nginx

```bash
sudo nano /etc/nginx/sites-enabled/wf.imcsh.com
```

在 **`location / {` 之前**插入 `deploy/nginx/wf.imcsh.com.production.patch.conf` 中的两段 `location`。

可在文件顶部（`server {` 外）增加：

```nginx
upstream imcwf_api {
    server 10.1.40.109:5320;
    keepalive 16;
}
```

### 3. 后端环境变量

```bash
export BEHIND_PROXY=true
export SESSION_COOKIE_SECURE=1
export FLASK_DEBUG=0
export TPC_SKIP_STARTUP_MAINTENANCE=1
```

写入 systemd 服务或 `backend` 启动脚本，然后重启后端。

**说明**：此前每次 `restart` 会同步跑数据库迁移与种子数据（`ensure_bootstrap`），导致启动需数十秒甚至更久。生产环境应设 `FLASK_DEBUG=0` 并跳过启动维护；**代码升级后**再手动执行一次：

```bash
cd /var/www/imcwf/backend
.venv/bin/python scripts/upgrade_db.py
```

### 4. 重载 Nginx

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### 5. 验证

```bash
curl -s https://wf.imcsh.com/api/v1/health
curl -s https://wf.imcsh.com/api/v1/auth/captcha
```

返回 JSON 即成功。再打开桌面客户端，验证码应能显示。

## 不影响 Web 的原因

| 请求 | 匹配规则 | 去向 |
|------|----------|------|
| `https://wf.imcsh.com/` | `location /` | 5321（不变） |
| `https://wf.imcsh.com/login` | `location /` | 5321（不变） |
| `https://wf.imcsh.com/api/v1/health` | `location /api/` | 5320（新增） |

仅新增更具体的 `/api/` 规则，不修改现有 `location /` 块。

## 附件上传

若客户端/Web 上传较大文件，可在 `location /api/` 内或 server 级将 `client_max_body_size` 调到 `64m`（与后端限制一致）。

## Windows 客户端下载

1. 在 **API 服务器（10.1.40.109）** 放置安装包：
   `/var/www/imcwf/deploy/downloads/TPCWorkflow.Client.exe`
2. Nginx 需包含 `location = /api/v1/client/download`（大文件关闭 `proxy_buffering`，超时 600s），见 `wf.imcsh.com.production.patch.conf`。
3. 验证：

```bash
curl -s https://wf.imcsh.com/api/v1/client/download-info -b 'session=...'
# available 应为 true

curl -I https://wf.imcsh.com/api/v1/client/download -b 'session=...'
# HTTP/1.1 200，Content-Length 约 76MB
```

若 exe 只放在 SSH 上传机（如 10.1.40.108）而 API 在 109，会出现浏览器「无法下载 - 没有文件」。
