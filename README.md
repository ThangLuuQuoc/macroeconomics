# macroeconomics

Theo dõi, trực quan hoá và giả lập tác động của các yếu tố vĩ mô lên kinh tế và thị trường chứng khoán Việt Nam. Công cụ cá nhân.

- Sản phẩm: [`.proofline/interview.md`](.proofline/interview.md)
- Nguồn dữ liệu: [`.proofline/data-sources.md`](.proofline/data-sources.md)
- Kiến trúc: [`docs/adr/001-stack.md`](docs/adr/001-stack.md)

## Chạy trên máy

Cần: Docker, [uv](https://docs.astral.sh/uv/), Node 22+ và pnpm 9.

```bash
docker compose up -d db                 # Postgres ở cổng 5544
uv sync
pnpm --dir web install
pnpm --dir web build                    # Bản build tĩnh vào web/out
uv run python -m macro.ingest           # Lấy dữ liệu từ các nguồn
uv run python -m macro.serve            # http://127.0.0.1:8070
```

Hoặc chạy cả app bằng Docker: `docker compose --profile app up --build`.

## Kiểm thử

```bash
docker compose up -d db
pnpm --dir web build
uv run playwright install chromium      # Lần đầu
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy
pnpm --dir web typecheck
```

Kịch bản người dùng (`tests/journeys/`) dựng app thật trên database riêng và nạp dữ liệu tổng hợp qua `python -m macro.ingest --raw-dir`, không gọi mạng.

## Cấu trúc

| Thư mục | Nội dung |
| :--- | :--- |
| `backend/macro/` | FastAPI, schema Postgres, connector nguồn dữ liệu, `ingest`, `serve` |
| `web/` | Next.js (xuất tĩnh), chỉ hiển thị số đã tính sẵn ở backend |
| `tests/` | pytest; `tests/journeys/` là kịch bản người dùng (Playwright) |
| `.proofline/` | Tài liệu sản phẩm, spec và báo cáo của Proofline |
