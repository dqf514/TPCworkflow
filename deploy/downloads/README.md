# Windows 客户端下载目录

将 `client/publish.ps1` 生成的文件放在此目录：

| 文件 | 说明 |
|------|------|
| `TPCWorkflow-Client.zip` | **推荐网页下载**（Edge 对 ZIP 拦截少于裸 exe） |
| `TPCWorkflow.Client.exe` | 单文件程序（zip 不存在时回退） |

## 重要：文件必须位于 API 服务器

生产环境 Nginx 将 `/api/` 转发到 **5320 后端进程所在机器**（见 `deploy/nginx/wf.imcsh.com.production.patch.conf`，当前为 `10.1.40.109:5320`）。

若你把 exe 只上传到 Web/SSH 机器（如 `10.1.40.108`），而后端跑在另一台机器，下载会提示「没有文件」。

**做法（二选一）：**

1. 把 `TPCWorkflow.Client.exe` 复制到 **API 服务器** 的项目目录：
   `/var/www/imcwf/deploy/downloads/TPCWorkflow.Client.exe`
2. 或在 API 服务器的 `.env` 中设置绝对路径：
   `CLIENT_DOWNLOAD_FILE=/path/to/TPCWorkflow.Client.exe`

上传后重启后端，并可用以下命令验证：

```bash
curl -s -b "session=你的cookie" https://wf.imcsh.com/api/v1/client/download-info
# 应返回 "available": true

curl -I -b "session=你的cookie" https://wf.imcsh.com/api/v1/client/download
# 应返回 200 且 Content-Length 约 76829841
```

Nginx 需为下载路由关闭缓冲（见 `wf.imcsh.com.production.patch.conf` 中 `location = /api/v1/client/download`）。
