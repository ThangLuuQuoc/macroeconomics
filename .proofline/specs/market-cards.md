# Spec: Thẻ thị trường chứng khoán Việt Nam (từ openstock)

> Tính năng thứ hai của `macroeconomics`. Trạng thái: **đã duyệt** (chủ dự án, 2026-10-27; journey blob `07e0aa5`).
> Liên quan: [`overview-dashboard.md`](overview-dashboard.md), [`../data-sources.md`](../data-sources.md) (connector 4 `openstock`).

## 1. Vấn đề

Bảng tổng quan mới có vĩ mô; chủ dự án muốn thấy ngay trên cùng trang thị trường chứng khoán đang phản ứng thế nào, lấy từ dữ liệu openstock đã có (không thu thập lại).

## 2. Phạm vi

**Làm:**

| Thẻ | `series_id` | Lấy từ `stock_db` | Hiển thị |
| :--- | :--- | :--- | :--- |
| VN-Index | `vn.vnindex` | `stock_prices`, `symbol = 'VNINDEX'`, `close` | `1.763,55`, kỳ là ngày giao dịch; **thay đổi bằng điểm và %**: `-10,60 điểm (-0,60%) so với phiên trước` |
| Giá trị giao dịch HOSE | `vn.hose_turnover` | `stock_prices`, `symbol = 'VNINDEX'`, `amount` (đồng) | `13,5 nghìn tỷ đồng`, `-20,1% so với phiên trước` |

- Thẻ thị trường đứng sau các thẻ vĩ mô Việt Nam, trước nhóm thế giới.
- Chuỗi ngày: không có dòng "so với cùng kỳ" (giống các chuỗi ngày khác).
- Nguồn hiển thị: `openstock · VNINDEX`.

**Không làm:**
- **Khối ngoại mua/bán ròng:** `stock_db` hiện chỉ có `stock_prices.foreign_net_value` từ 24/06 đến 28/08/2026 và `quotes` là ảnh chụp trong ngày của 1.117/3.616 mã. Cộng lại sẽ ra số sai (thiếu mã, thiếu ngày), nên chuỗi `vn.foreign_net` ghi `blocked` trong registry, **không hiện thẻ** (T-4). Mở lại khi openstock lưu đủ lịch sử khối ngoại.
- VN30, HNX-Index, UPCoM-Index, biểu đồ: để sau.

## 3. Connector `openstock`

- `fetch`: kết nối `stock_db` bằng **tài khoản chỉ đọc** (chuỗi kết nối trong biến môi trường `MACRO_OPENSTOCK_URL`, không ghi vào repo), đọc lịch sử `VNINDEX` (ngày, `close`, `amount`) và lưu bản gốc thành `VNINDEX.csv` (`time,close,amount`) trong thư mục raw. Không ghi gì vào `stock_db`.
- `parse`: đọc `VNINDEX.csv` → hai chuỗi `vn.vnindex`, `vn.hose_turnover`.
- Thiếu `MACRO_OPENSTOCK_URL` hoặc không kết nối được: lần lấy là lỗi (T-4: giữ số cũ, nhãn "Nguồn lỗi"); các connector khác vẫn chạy.

## 4. Tiêu chí nghiệm thu

Kiểm bằng `tests/journeys/test_market_cards.py` (Playwright, bản gốc tổng hợp viết trong journey):

1. Thẻ VN-Index hiện `1.763,55`, kỳ `26/10/2026`, `-10,60 điểm (-0,60%)` so với phiên trước, nguồn `openstock · VNINDEX`, không có dòng so cùng kỳ.
2. Thẻ giá trị giao dịch HOSE hiện `13,5 nghìn tỷ đồng`, `-20,1%` so với phiên trước.
3. Không có thẻ khối ngoại (`indicator-vn.foreign_net`) dù bản gốc có cột giá trị khối ngoại.
4. openstock lỗi ở lần lấy sau thì thẻ VN-Index giữ `1.763,55` kèm nhãn "Nguồn lỗi".

## 5. Quyết định của chủ dự án (2026-10-27)

1. Duyệt spec và acceptance journey v1.
2. **Tạo role chỉ đọc `macro_reader`** trong `stock_db`: chỉ `CONNECT` database, `USAGE` schema `public` và `SELECT` trên `stock_prices`. Chuỗi kết nối nằm trong `.env` của repo (đã nằm trong `.gitignore`), không commit.
3. Merge `proofline/feature-overview-dashboard` vào `main` trước, rồi làm tính năng và chạy `verify` với base `main`.
