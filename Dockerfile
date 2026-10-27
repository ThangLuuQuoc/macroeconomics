# Build web tĩnh, rồi chạy FastAPI phục vụ cả /api lẫn bản build (ADR-001).
FROM node:22-bookworm-slim AS web
WORKDIR /app/web
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.6.10 /uv /bin/uv
WORKDIR /app
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend ./backend
RUN uv sync --frozen --no-dev
COPY --from=web /app/web/out ./web/out
ENV MACRO_WEB_DIR=/app/web/out
EXPOSE 8070
CMD ["uv", "run", "--no-dev", "python", "-m", "macro.serve", "--host", "0.0.0.0", "--port", "8070"]
