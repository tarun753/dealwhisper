# ── Stage 1: Build frontend ────────────────────────────────────
FROM node:22-slim AS frontend-build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts

COPY tsconfig.json tsconfig.app.json tsconfig.node.json vite.config.ts ./
COPY src ./src
COPY index.html ./

RUN npm run build

# ── Stage 2: Production backend + static frontend ─────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY --from=frontend-build /app/dist /app/static

CMD ["uvicorn", "dealwhisper_backend.server:app", "--host", "0.0.0.0", "--port", "8080"]
