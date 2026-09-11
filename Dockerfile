# Backend — FastAPI content engine.
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so this layer is cached across code
# changes that don't touch requirements.txt.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
