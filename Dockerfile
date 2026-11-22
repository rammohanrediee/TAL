FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.2.0" \
    && pip install --no-cache-dir .

COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY start-api.sh ./start-api.sh

RUN chmod 755 /app/start-api.sh \
    && useradd --system --uid 10001 --create-home tal
USER tal

EXPOSE 8000
CMD ["/app/start-api.sh"]
