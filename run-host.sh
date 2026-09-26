#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [ -f "${SCRIPT_DIR}/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.env"
    set +a
fi

export DB_PATH="${DB_PATH:-${SCRIPT_DIR}/data/wechat_redeem.db}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

# 优先级：.venv-host (生产宿主应急隔离环境) > .venv (本地标准虚拟环境) > PATH 中的 Python
PYTHON_BIN=""
if [ -x "${SCRIPT_DIR}/.venv-host/bin/python" ]; then
    PYTHON_BIN="${SCRIPT_DIR}/.venv-host/bin/python"
elif [ -x "${SCRIPT_DIR}/.venv/bin/python" ]; then
    PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "ERROR: 未找到可用的 Python 解释器（请检查 .venv-host / .venv 或安装 python3）" >&2
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting WeChat Redeem Hub via Host Runner: ${PYTHON_BIN} on ${HOST}:${PORT} (DB: ${DB_PATH})"
exec "${PYTHON_BIN}" -m uvicorn app:app --host "${HOST}" --port "${PORT}" --app-dir "${SCRIPT_DIR}"
