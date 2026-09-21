FROM node:22-alpine AS web-build

WORKDIR /src/web
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
COPY web/index.html web/vite.config.js ./
COPY web/src ./src
RUN corepack enable && pnpm install --frozen-lockfile && pnpm build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WECHAT_ARCHIVE_DB=/data/archive.db \
    WECHAT_ARCHIVE_ROOT=/data \
    WECHAT_IMPORT_ROOT=/imports

WORKDIR /app
COPY pyproject.toml ./
COPY archive_core ./archive_core
COPY backend ./backend
COPY tools ./tools
COPY --from=web-build /src/web/dist ./web/dist
RUN pip install --no-cache-dir .

RUN mkdir -p /data /imports
VOLUME ["/data", "/imports"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
