# ---- frontend build ----
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- runtime ----
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple \
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
