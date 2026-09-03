FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn pydantic -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY app.py config.py /app/
COPY db/ /app/db/
COPY core/ /app/core/
COPY routes/ /app/routes/
EXPOSE 8000
VOLUME ["/data"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
