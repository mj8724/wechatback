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
RUN pip install --no-cache-dir fastapi uvicorn pydantic -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY app.py config.py /app/
COPY db/ /app/db/
COPY core/ /app/core/
COPY routes/ /app/routes/
COPY --from=frontend /build/dist /app/frontend/dist
EXPOSE 8000
VOLUME ["/data"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
