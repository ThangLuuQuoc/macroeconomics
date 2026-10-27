# ADR-001: Stack và cấu trúc của walking skeleton

- **Trạng thái:** đã duyệt (chủ dự án, 2026-10-27)
- **Ngày:** 2026-10-27
- **Liên quan:** `.proofline/interview.md`, `.proofline/data-sources.md`, `.proofline/specs/overview-dashboard.md`

## Bối cảnh

- Công cụ cá nhân, một người dùng, chạy trên máy cá nhân (Windows + Docker).
- Phần nặng là dữ liệu chuỗi thời gian và mô hình kinh tế lượng (VAR/BVAR, kịch bản) → hệ sinh thái Python.
- Chủ dự án đã chọn: **Python (FastAPI, pandas, statsmodels) + Postgres + Next.js** (phỏng vấn 2026-10-27).
- Gu đã tuyên bố: mọi nguồn qua adapter (T-3); nguồn lỗi thì giữ số cũ, không điền số đoán (T-4); logic dùng ở 2 chỗ thì tách ngay (T-1).
- Proofline cần: test xuất JUnit, kịch bản người dùng chạy trên trình duyệt thật, app khởi chạy được bằng một lệnh.

## Quyết định

1. **Một repo, hai phần:**
   - `backend/macro/`: Python 3.12, quản lý bằng `uv`. FastAPI cho API, `psycopg` 3 + SQL thuần cho Postgres (schema trong `schema.sql`), pandas cho xử lý chuỗi. Chưa dùng ORM: schema nhỏ, truy vấn chuỗi thời gian viết SQL rõ hơn.
   - `web/`: Next.js + TypeScript, **xuất tĩnh** (`output: "export"`). Trang gọi API cùng origin (`/api/...`) từ trình duyệt.
2. **Một tiến trình phục vụ:** FastAPI phục vụ cả `/api/*` lẫn bản build tĩnh của `web/` (`web/out`). Một người dùng không cần SSR; một tiến trình thì chạy, đóng gói Docker và kiểm thử đơn giản hơn nhiều so với chạy song song server Next.js.
3. **Tính toán chỉ ở backend:** Next.js chỉ hiển thị số đã tính và đã định dạng sẵn (định dạng số kiểu Việt Nam, `5,08%`). Tránh hai nơi tính cùng một con số.
4. **Dữ liệu:**
   - Bảng `series` (registry, có trạng thái `verified`/`partial`/`needs_mapping`/`blocked`), `fetch_runs` (mỗi lần lấy dữ liệu của một connector: thành công hay lỗi, lúc nào, lỗi gì), `observations` (giá trị theo kỳ, **mỗi lần lấy một bản**, để giữ phiên bản số liệu).
   - Interface `Connector`: `fetch()` tải bản gốc về thư mục raw; `parse()` đọc bản gốc thành quan sát chuẩn hoá. Đổi nguồn chỉ đổi connector.
   - Lệnh `python -m macro.ingest`: chạy các connector; `--raw-dir` đọc bản gốc có sẵn (không gọi mạng) để kiểm thử và để nạp lại.
5. **Postgres 16** chạy bằng Docker Compose (cổng máy `5544`, tránh các Postgres đang có trên máy).
6. **Kiểm thử:** pytest (xuất JUnit) cho cả test đơn vị lẫn kịch bản người dùng; kịch bản người dùng dùng **Playwright cho Python** (`pytest-playwright`), mỗi test tạo một database riêng và nạp dữ liệu qua đúng đường `ingest --raw-dir`.
7. **Chất lượng:** `ruff` (lint + format) và `mypy` cho Python; `tsc --noEmit` cho web; GitHub Actions chạy tất cả.

## Phương án đã cân nhắc

| Phương án | Vì sao không chọn |
| :--- | :--- |
| Next.js chạy server riêng (SSR) + FastAPI | Hai tiến trình, hai cổng, test phải khởi chạy cả hai; không có lợi ích gì cho một người dùng |
| Python thuần (Streamlit / HTMX) | Chủ dự án đã chọn Next.js cho giao diện |
| ORM (SQLAlchemy) | Chưa cần; có thể thêm khi schema lớn lên |

## Hệ quả

- Build web (`pnpm --dir web build`) phải chạy trước khi chạy app hoặc kịch bản người dùng; lệnh cài đặt của Proofline làm việc này.
- Kịch bản người dùng cần Postgres đang chạy (`docker compose up -d db`).
- Không có SSR/SEO: chấp nhận được với công cụ cá nhân.
