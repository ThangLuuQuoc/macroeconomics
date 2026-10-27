# Spec: Bảng tổng quan vĩ mô

> Tính năng đầu tiên của `macroeconomics` (luồng A). Trạng thái: **chờ chủ dự án duyệt** spec và acceptance journey.
> Liên quan: [`../interview.md`](../interview.md), [`../data-sources.md`](../data-sources.md); nguyên tắc T-1…T-4 trong `tech-lead-taste.md`.

## 1. Vấn đề

Chủ dự án muốn theo dõi sức khoẻ kinh tế Việt Nam và các yếu tố bên ngoài ảnh hưởng tới nó ở **một trang**, thay vì mở nhiều website. Mỗi con số phải trả lời được ngay ba câu: **bao nhiêu, của kỳ nào, lấy từ đâu**, và có đang cũ hay không.

## 2. Người dùng và mục tiêu

- Một người dùng (chủ dự án), chạy trên máy cá nhân.
- Mở trang chủ là thấy các chỉ số chính, giá trị mới nhất, thay đổi so với kỳ trước và so với cùng kỳ năm trước.

## 3. Phạm vi

**Làm:**

| Nhóm | Chỉ số (thẻ) | `series_id` | Connector |
| :--- | :--- | :--- | :--- |
| Việt Nam | Tăng trưởng GDP thực (so cùng kỳ, quý) | `vn.gdp_real_yoy` | dautubenvung |
| | CPI (so cùng kỳ) | `vn.cpi_yoy` | dautubenvung |
| | Xuất khẩu (tháng) | `vn.exports` | dautubenvung |
| | Nhập khẩu (tháng) | `vn.imports` | dautubenvung |
| | FDI thực hiện (tháng) | `vn.fdi_disbursed` | dautubenvung |
| | Tổng mức bán lẻ hàng hoá & dịch vụ (tháng) | `vn.retail` | dautubenvung |
| | IIP | `vn.iip` | dautubenvung |
| | PMI sản xuất | `vn.pmi_mfg` | dautubenvung |
| | Lãi suất tái cấp vốn | `vn.refinance_rate` | dautubenvung |
| Thế giới | Lợi suất trái phiếu Mỹ 10 năm | `us.ust10y` | fred (`DGS10`) |
| | Chỉ số USD rộng (Fed) | `us.usd_broad` | fred (`DTWEXBGS`) |
| | Dầu Brent | `global.brent` | wb_pinksheet |
| | Vàng | `global.gold` | wb_pinksheet |

Mỗi thẻ hiển thị:
- **Giá trị mới nhất** kèm đơn vị, định dạng số kiểu Việt Nam (dấu phẩy thập phân: `5,08%`).
- **Kỳ** của giá trị: `09/2026` (tháng), `Q3/2026` (quý), `23/10/2026` (ngày).
- **Thay đổi so với kỳ trước** và **so với cùng kỳ năm trước** khi có đủ dữ liệu:
  - chỉ số là tỷ lệ (CPI, lãi suất, lợi suất, PMI…): chênh lệch tuyệt đối, đơn vị **điểm** (`+0,13 điểm %` với tỷ lệ phần trăm, `+1,5 điểm` với PMI);
  - chỉ số là mức (xuất khẩu, bán lẻ, dầu…): phần trăm thay đổi (`+2,5%`).
- **Nguồn**: tên connector và mã chuỗi gốc khi có (`FRED · DGS10`, `World Bank Pink Sheet`, `dautubenvung.vn`).
- **Trạng thái nguồn** (T-4): bình thường thì không có nhãn; nguồn lỗi ở lần lấy gần nhất thì giữ giá trị cũ và hiện nhãn **"Nguồn lỗi"** kèm "số liệu đến <kỳ>, lấy lần cuối <thời điểm>".

**Không làm (để sau):**
- VN-Index, khối ngoại (openstock): spec kế tiếp.
- Biểu đồ chi tiết từng chỉ số, giả lập kịch bản, nowcast.
- Tỷ giá USD/VND, tín dụng, xuất khẩu theo thị trường, Trung Quốc/EU, GPR: chờ connector `sbv`, `comtrade`, `dbnomics`, `gpr`.
- Đăng nhập, nhiều người dùng.
- Lịch tự động lấy dữ liệu: tính năng này chỉ cần lệnh `ingest` chạy tay; lịch chạy để spec sau.

## 4. Quy tắc dữ liệu

1. **Không có số đoán** (T-4): không nội suy, không điền chỗ thiếu. Thiếu kỳ trước hoặc cùng kỳ thì không hiển thị dòng thay đổi tương ứng.
2. **Đúng tên thứ được đo:** thẻ USD ghi "Chỉ số USD rộng (Fed)", **không** dùng chữ "DXY" ở đâu trên trang.
3. **Tính toán chỉ ở backend Python**: Next.js chỉ hiển thị số đã tính và đã định dạng sẵn từ API (đề xuất mặc định cho câu gu "logic tính toán nằm ở đâu", chờ xác nhận). Tăng trưởng so cùng kỳ là **một hàm dùng chung** cho mọi chỉ số (T-1).
4. **Nguồn qua adapter** (T-3): trang không biết dữ liệu đến từ dautubenvung hay FRED; chỉ đọc bảng chuỗi số liệu chuẩn hoá trong Postgres.
5. Chỉ hiển thị chuỗi có trạng thái `verified` hoặc `partial` trong registry.

## 5. Tiêu chí nghiệm thu

Kiểm bằng acceptance journey `tests/journeys/test_overview_dashboard.py` (Playwright, chạy như người dùng thật). Dữ liệu vào là **bản ghi nguồn tổng hợp viết ngay trong journey** (không gọi mạng), nạp qua đúng đường ingest của app:

1. **Giá trị, kỳ, nguồn:** với dữ liệu mẫu, thẻ CPI hiện `5,08%`, kỳ `09/2026`, `+0,13 điểm %` so với tháng trước, nguồn `dautubenvung.vn`; thẻ PMI hiện `51,9`, `+1,5 điểm`; thẻ lợi suất Mỹ 10 năm hiện `5,00%`, kỳ `23/10/2026`, nguồn `FRED · DGS10`; thẻ dầu Brent hiện `82,30 USD/thùng`, kỳ `09/2026`, `+2,7%` so với tháng trước; thẻ USD có tên "Chỉ số USD rộng (Fed)" và trang không có chữ "DXY".
2. **So cùng kỳ:** thẻ xuất khẩu hiện `+2,5%` so với tháng trước và `+29,3%` so với cùng kỳ; khi thiếu số cùng kỳ năm trước thì không hiện dòng so cùng kỳ (không đoán).
3. **Nguồn lỗi (T-4):** lần ingest đầu thành công, lần sau FRED lỗi → thẻ lợi suất Mỹ vẫn hiện `5,00%` của `23/10/2026` kèm nhãn **"Nguồn lỗi"**; các thẻ của nguồn khác không có nhãn này.

Ngoài journey, các gate chung của Proofline: không regression, test mới cho phần tính toán (hàm tăng trưởng, định dạng số, adapter đọc bản ghi nguồn), typecheck/lint sạch.

## 6. Điều kiện trước: walking skeleton

Journey phải **fail ở khẳng định trên base** rồi **pass trên nhánh**, nên base phải là một khung chạy được, chưa có bảng tổng quan. Walking skeleton (PR riêng, commit lên `main`) gồm:

- **Cấu trúc:** `backend/` (Python 3.12, uv, FastAPI, SQLAlchemy/psycopg, pandas), `web/` (Next.js, TypeScript), `tests/` (pytest), `docker-compose.yml` (Postgres 16), `Dockerfile`, CI (GitHub Actions) chạy lint, typecheck, test.
- **Khung dữ liệu:** bảng `series` (registry), `observations`, `fetch_runs` (lần lấy, thành công/lỗi, thời điểm); interface `Connector` (fetch → raw, parse raw → quan sát chuẩn hoá); lệnh `python -m macro.ingest` (có chế độ `--raw-dir` đọc bản ghi nguồn từ thư mục, không gọi mạng).
- **Trang chủ** `web/` hiển thị khung trống (tiêu đề "Tổng quan vĩ mô", chưa có thẻ).
- **Hạ tầng test journey** (`tests/journeys/` là package, có `__init__.py`):
  - `conftest.py`: fixture `macro_app` trả về hàm `macro_app(rounds) -> url`: tạo DB test sạch; với mỗi vòng (dict `connector → bản ghi nguồn` hoặc lỗi giả) ghi vào thư mục tạm và chạy `ingest --raw-dir`; khởi chạy API + web; trả về URL trang chủ. Dùng fixture `page` của `pytest-playwright`.
  - `support.py`: hàm dựng bản ghi nguồn theo đúng định dạng gốc: `dautubenvung_payload(**datasets)` (JSON như `/api/data-vi-mo`), `fred_csv(series_id, rows)` (CSV như `fredgraph.csv`), `pink_sheet_xlsx(months)` (xlsx như `CMO-Historical-Data-Monthly.xlsx`), `source_failure(connector, error)`.
- **Hợp đồng giao diện:** mỗi thẻ có `data-testid="indicator-<series_id>"`, bên trong `value`, `period`, `change-prev`, `change-yoy`, `source`, `status`.
- **Cấu hình Proofline:** cập nhật `targets/macroeconomics/target.yaml` (`commands.install`, `test_junit`, `typecheck`, `lint`, `app_runtime`, `journeys_dir: tests/journeys`).

Kiến trúc chọn ở đây cần một ADR ngắn (`docs/adr/001-stack.md`) do chủ dự án duyệt cùng PR skeleton.

## 7. Quyết định của chủ dự án (2026-10-27)

- **Duyệt spec và acceptance journey v1** (blob `9ecfd34`, ghi bằng `proofline spec approve`).
- **Định dạng số kiểu Việt Nam** (`5,08%`, dấu phẩy thập phân) cho toàn bộ giao diện.

**Còn mở:**
1. Đơn vị của các chuỗi dautubenvung (xuất khẩu, FDI, bán lẻ: triệu hay tỷ USD/VND) phải đối chiếu với GSO khi làm adapter; journey cố ý chỉ khẳng định các thẻ có đơn vị chắc chắn (%, điểm, USD/thùng) và phần trăm thay đổi.
2. Các câu gu chưa trả lời (test và mock, dependency, giải pháp tạm, tầng đặt logic, câu hỏi đầu tiên khi nhận bug): spec dùng đề xuất mặc định ở mục 4.3.
