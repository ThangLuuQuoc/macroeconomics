# Nguồn dữ liệu và registry chuỗi số liệu

> Kế hoạch nguồn dữ liệu của `macroeconomics`, đã đối chiếu trực tiếp với từng nguồn ngày 2026-10-27.
> Nguyên tắc liên quan trong `tech-lead-taste.md`: **T-3** (mọi nguồn qua adapter), **T-4** (nguồn lỗi thì giữ số cũ và báo rõ, không điền số đoán).

## 1. Nguyên tắc

1. **Đã chọn nguồn ≠ đã có dữ liệu.** Mỗi chuỗi có trạng thái trong registry; giao diện chỉ hiển thị chuỗi `verified` hoặc `partial` (kèm ghi chú).
2. **Không dùng chuỗi thay thế rồi giữ nhãn cũ.** Chuỗi đo thứ khác phải mang tên của chính nó (trường `measures`). Không có dữ liệu thì để trống, ghi rõ thiếu.
3. **Tách lấy dữ liệu khỏi chuẩn hoá:** adapter chỉ tải và lưu bản gốc (raw); bước chuẩn hoá đọc raw, kiểm tra chất lượng rồi mới ghi vào DB. Đổi nguồn chỉ đổi adapter (T-3).
4. **Lưu phiên bản (vintage):** GDP, CPI, GPR… có thể bị sửa lại; mỗi lần lấy ghi lại thời điểm và giá trị, mô hình biết mình đã chạy trên bản số liệu nào.
5. **Lấy dữ liệu nhẹ nhàng:** theo lịch thưa, đọc từ DB của app, không gọi nguồn mỗi lần mở trang.

```text
dautubenvung API ───┐
FRED API ───────────┤
WB Pink Sheet file ─┤
openstock stock_db ─┼── raw storage ── normalize ── quality checks ── Postgres (series, observations, vintages)
DBnomics API ───────┤
Comtrade API ───────┤
NHNN công bố ───────┤
GPR file ───────────┘
```

## 2. Registry (bản ghi cho mỗi chuỗi)

```python
class SeriesStatus(StrEnum):
    VERIFIED = "verified"  # Đã lấy được, đúng định nghĩa, lịch sử và độ mới đã kiểm
    PARTIAL = "partial"  # Lấy được nhưng thiếu kỳ / lịch sử ngắn / chưa đủ chi tiết
    NEEDS_MAPPING = "needs_mapping"  # Đã biết nguồn, chưa xác định mã chuỗi hoặc cách đọc
    BLOCKED = "blocked"  # Không có nguồn dùng được (trả phí, không công bố…)


class Series(BaseModel):
    id: str  # vd "vn.cpi_yoy", "us.ust10y"
    name: str  # Tên hiển thị, đúng với thứ được đo
    measures: str  # Thực sự đo cái gì (bắt buộc rõ với chuỗi đối chiếu/thay thế)
    connector: (
        str  # dautubenvung | fred | wb_pinksheet | openstock | dbnomics | comtrade | sbv | gpr
    )
    upstream_provider: str  # Nhà cung cấp gốc: GSO, Fed St. Louis, World Bank, NBS…
    source_series_id: str | None  # Mã ở nguồn: "DGS10", "cpi.CPI", "IMF/IFS/M.VN.32D___XDC"…
    frequency: Literal["D", "W", "M", "Q", "A"]
    unit: str  # "%", "% so cùng kỳ", "điểm", "USD/thùng", "triệu USD"…
    transform: Literal["level", "yoy", "mom", "index"]
    seasonal_adjustment: bool
    first_period: str | None
    last_period: str | None
    status: SeriesStatus
    is_proxy: bool  # True nếu là chuỗi đối chiếu/thay thế cho thứ ta thực sự muốn đo
    definition: str
    source_url: str
    terms_note: str  # Điều khoản sử dụng / rủi ro đã biết
    last_checked_at: datetime
```

## 3. Connector

| # | Connector | Dữ liệu | Cách lấy | Đã kiểm (2026-10-27) | Giới hạn |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **dautubenvung** | Lõi vĩ mô Việt Nam: GDP, CPI, bán lẻ, xuất nhập khẩu tổng, FDI, vốn NSNN, IIP, PMI chỉ số chính, lãi suất điều hành/liên ngân hàng; Mỹ cơ bản | API nội bộ `/api/data-vi-mo`, `/api/lai-suat-ngan-hang`, `/api/data-the-gioi` | Có dữ liệu tới 09/2026 (chi tiết ở `interview.md` mục 5) | Không công khai, có thể đổi, một phần khoá sau gói trả phí; `robots.txt`: `use=reference`. Chủ dự án chấp nhận rủi ro, dùng qua adapter, sẽ chuyển vào openstock |
| 2 | **fred** | Lợi suất UST 10 năm, chỉ số USD rộng của Fed, EPU | CSV `fredgraph.csv?id=<mã>` (hoặc API có key) | `DGS10` 1962 → 23/10/2026; `DTWEXBGS` 2006 → 23/10/2026; `GEPUCURRENT` 1997 → 07/2026 (tháng, trễ ~3 tháng); `USEPUINDXD` 1985 → 25/10/2026 | `DTWEXBGS` là **chỉ số USD rộng của Fed, không phải DXY**: giữ đúng tên |
| 3 | **wb_pinksheet** | Giá dầu, vàng quốc tế theo tháng | File `CMO-Historical-Data-Monthly.xlsx` | Có file | Đường dẫn chứa mã đổi theo kỳ phát hành: adapter **tìm link trên trang** `worldbank.org/en/research/commodity-markets`, không ghi cứng. Không phải giá vàng trong nước hay giá realtime |
| 4 | **openstock** | VN-Index, thanh khoản, khối ngoại | Đọc `stock_db` (Postgres, tài khoản chỉ đọc) | `stock_db` 40 bảng, giá mới nhất 23/10/2026 | Cần tạo tài khoản chỉ đọc; app chạy cùng máy |
| 5 | **dbnomics** | Quốc tế: Trung Quốc (NBS), EU (Eurostat), OECD, BIS | REST `api.db.nomics.world/v22`, mã `provider/dataset/series` lấy từ "Copy API link" | Có các provider NBS, Eurostat, IMF, WB, OECD, BIS | **IMF/IFS của Việt Nam đã cũ**: tín dụng khu vực tư nhân và M2 chỉ tới 11/2023, tỷ giá tới 06/2025, bộ IFS cập nhật lần cuối 08/2025 → **không dùng thay NHNN**, chỉ để bù lịch sử cũ (ghi rõ nguồn) |
| 6 | **comtrade** | Xuất khẩu theo thị trường và mặt hàng (HS) | API UN Comtrade (key miễn phí) | **Việt Nam tự báo cáo dữ liệu tháng chỉ tới 12/2023** (các tháng 2024–2026 trống). **Dữ liệu đối chiếu có**: nhập khẩu của Mỹ từ Việt Nam đã có tới 06/2026 | Dùng **dữ liệu đối chiếu**: nhập khẩu của Mỹ, Trung Quốc, EU, Nhật, Hàn từ Việt Nam. Là phép đo khác (giá CIF thay vì FOB, lệch thời điểm, hàng tái xuất): `is_proxy: true`, tên dạng "Nhập khẩu của Mỹ từ Việt Nam (số liệu Mỹ)", **không** gọi là "xuất khẩu của Việt Nam". Kiểm quota, độ trễ từng đối tác |
| 7 | **sbv** (NHNN) | Tỷ giá USD/VND, tín dụng, tổng phương tiện thanh toán, lãi suất | ETL từ số liệu công bố (bảng/file trên website) | Chưa xác minh đường tải tự động | **Nguồn duy nhất cho tiền tệ và tín dụng hiện tại.** Tự xây connector; tỷ giá trung tâm và tỷ giá giao dịch là **hai chuỗi khác nhau** |
| 8 | **gpr** | Chỉ số rủi ro địa chính trị (toàn cầu, theo nước) | File `.xls` trên trang tác giả (`data_gpr_export.xls`, `data_gpr_daily_recent.xls`) | Tải được cả hai file | Không phải API; số liệu gần đây có thể được sửa lại → lưu vintage |

## 4. Bảng đối chiếu nhu cầu

| Cần | Connector | Trạng thái ban đầu | Ghi chú |
| :--- | :--- | :--- | :--- |
| GDP, CPI, bán lẻ, IIP, FDI, vốn NSNN, PMI chỉ số chính | dautubenvung | `verified` | CPI chỉ từ 2021 → `partial` cho mô hình |
| Xuất nhập khẩu tổng | dautubenvung | `verified` | Không theo mặt hàng/thị trường |
| Xuất khẩu theo thị trường, mặt hàng | comtrade (đối chiếu) | `needs_mapping` | `is_proxy: true` |
| USD/VND | sbv | `needs_mapping` | Chọn rõ trung tâm hay giao dịch |
| Tín dụng, tổng phương tiện thanh toán | sbv | `needs_mapping` | IMF qua DBnomics đã cũ (11/2023) |
| PMI đơn hàng mới, đơn hàng xuất khẩu | — | `blocked` | S&P Global trả phí. Có thể tự trích chiều tăng/giảm từ thông cáo thành chuỗi định tính riêng, **không** gọi là chỉ số PMI thành phần |
| Dầu Brent, vàng | wb_pinksheet | `verified` | Giá quốc tế theo tháng |
| Lợi suất UST 10 năm | fred `DGS10` | `verified` | |
| Sức mạnh USD | fred `DTWEXBGS` | `verified` | Tên: "Chỉ số USD rộng (Fed)", không phải DXY |
| EPU toàn cầu, Mỹ | fred `GEPUCURRENT`, `USEPUINDXD` | `verified` | |
| GPR | gpr | `verified` | |
| Trung Quốc, EU | dbnomics (NBS, Eurostat) | `needs_mapping` | Cụ thể hoá từng chỉ tiêu (GDP, CPI/HICP, sản xuất, bán lẻ); EU khác Euro Area |
| Cước container | — | `blocked` | Chưa có nguồn miễn phí đủ lịch sử. Để thiếu, **không** thay bằng chỉ số logistics khác |
| VN-Index, khối ngoại | openstock | `verified` | |

## 5. Theo giai đoạn

- **Bảng tổng quan (tính năng đầu tiên):** chỉ dùng **dautubenvung + fred + wb_pinksheet**.
- **Kế tiếp:** openstock (VN-Index, khối ngoại).
- **Giả lập kịch bản:** sbv, comtrade (đối chiếu), dbnomics, gpr.
