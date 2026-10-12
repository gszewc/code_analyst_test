FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY codeminer ./codeminer
COPY docker/wait_for_neo4j.py ./docker/wait_for_neo4j.py
COPY .env.example ./.env.example
COPY README.md ./README.md

RUN mkdir -p data uploads logs

EXPOSE 8080

CMD ["sh", "-c", "python /app/docker/wait_for_neo4j.py && uvicorn codeminer.api.main:app --host 0.0.0.0 --port 8080"]
