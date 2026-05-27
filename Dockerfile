# syntax=docker/dockerfile:1.6
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels openemployee-core \
 && rm -rf /wheels

EXPOSE 8080
CMD ["uvicorn", "openemployee_core.smoke.app:app", "--host", "0.0.0.0", "--port", "8080"]
