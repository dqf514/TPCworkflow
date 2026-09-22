#!/usr/bin/env bash
# IMC Workflow 系统日志清理（登录/访问、邮件通知）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${BACKEND_DIR}"

if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
elif [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

echo "========================================"
echo " IMC Workflow 系统日志清理"
echo "========================================"
echo "工作目录：${BACKEND_DIR}"
echo ""
echo "将清理以下数据（不影响审批单及其审批环节历史）："
echo "  · login_access_logs   登录 / 访问日志"
echo "  · notification_logs   邮件发送日志"
echo "  · task_email_tokens   已过期的邮件审批令牌"
echo ""
echo "请选择："
echo "  1) 全量清理"
echo "  2) 清理 30 天前的日志"
echo "  3) 退出"
echo ""
read -r -p "请输入选项 [1-3]: " choice

case "${choice}" in
  1)
    MODE="all"
    DESC="全量清理"
    ;;
  2)
    MODE="days"
    DESC="清理 30 天前的日志"
    ;;
  3)
    echo "已取消。"
    exit 0
    ;;
  *)
    echo "无效选项，已取消。"
    exit 1
    ;;
esac

echo ""
read -r -p "确认执行「${DESC}」？此操作不可恢复 [y/N]: " confirm
if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
  echo "已取消。"
  exit 0
fi

echo ""
"${PYTHON_BIN}" "${SCRIPT_DIR}/cleanup_system_logs.py" --mode "${MODE}"
echo ""
echo "完成。"
