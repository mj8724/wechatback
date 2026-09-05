# ---- frontend build ----
# 钉死 bookworm：浮动 slim 在 2025-09-01 切到 trixie，本仓库宿主（Debian13+VMware）上 trixie 用户态触发 ld.so 断言。勿改回浮动标签。
FROM node:20-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- runtime ----
# 钉死 bookworm：python:3.11-slim 于 2025-09-01 从 bookworm 切到 trixie（glibc 2.41 + OpenSSL 3.5），
# 在本宿主上 import ssl/hashlib 必崩（Exited 127，ld.so elf_machine_rela_relative 断言）。勿改回浮动标签。
FROM python:3.11-slim-bookworm
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
 && python -c "import ssl, hashlib; print('ssl-ok', ssl.OPENSSL_VERSION)" \
 && python -c "import fastapi, uvicorn; print('api-ok')" \
 && useradd -m appuser \
 && mkdir -p /data /app/frontend && chown -R appuser:appuser /data /app
COPY app.py config.py /app/
COPY db/ /app/db/
COPY core/ /app/core/
COPY routes/ /app/routes/
COPY --from=frontend /build/dist /app/frontend/dist
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
