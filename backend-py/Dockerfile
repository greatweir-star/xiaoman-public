FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    XIAOMAN_DATA_DIR=/app/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 18789

CMD ["sh", "-c", "python -m app.migrations.run && exec uvicorn main:app --host 0.0.0.0 --port 18789"]
