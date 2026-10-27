# Spec: Giả lập kịch bản (local projections)

> Tính năng thứ ba của `macroeconomics`. Trạng thái: **đã duyệt** (chủ dự án, 2026-10-27).
> Liên quan: [`../interview.md`](../interview.md) mục 2, [`../data-sources.md`](../data-sources.md); nguyên tắc T-1…T-4.

## 1. Vấn đề

Chủ dự án muốn hỏi "nếu giá dầu tăng 20% (hay lợi suất Mỹ tăng 0,5 điểm, USD mạnh lên 5%) thì xuất khẩu, sản xuất, lạm phát và VN-Index của Việt Nam phản ứng thế nào trong 12 tháng tới", và thấy **độ chắc chắn** của câu trả lời, không chỉ một con số.

## 2. Phạm vi

**Cú sốc** (yếu tố bên ngoài; Việt Nam không tác động ngược lại được):

| Cú sốc | `series_id` | Biến cú sốc theo tháng `x_t` | Đơn vị độ lớn |
| :--- | :--- | :--- | :--- |
| Giá dầu Brent | `global.brent` | `100·Δln(giá tháng)` | % |
| Lợi suất trái phiếu Mỹ 10 năm | `us.ust10y` | `Δ(trung bình tháng)` | điểm % |
| Chỉ số USD rộng (Fed) | `us.usd_broad` | `100·Δln(trung bình tháng)` | % |

**Biến kết quả** (theo tháng):

| Biến | `series_id` | Biến dùng trong mô hình `y_t` | Đơn vị phản ứng |
| :--- | :--- | :--- | :--- |
| Xuất khẩu | `vn.exports` | Tăng trưởng so cùng kỳ: `(X_t / X_{t-12} − 1)·100` | điểm % (tăng trưởng so cùng kỳ) |
| IIP | `vn.iip` | Giá trị % so cùng kỳ như nguồn | điểm % |
| PMI sản xuất | `vn.pmi_mfg` | Mức điểm | điểm |
| CPI (so cùng kỳ) | `vn.cpi_yoy_long` (nối, mục 3) | % so cùng kỳ | điểm % |
| VN-Index | `vn.vnindex` | `100·ln(đóng cửa cuối tháng)` | % |

**Mô hình: local projections (Jordà)**, ước lượng riêng cho từng biến kết quả, trên **lịch sử dài nhất của chính nó** (không ép về mẫu chung):

```
y_{t+h} − y_{t−1} = α_h + β_h·x_t + Σ_{l=1..2} (γ_{h,l}·Δy_{t−l} + δ_{h,l}·x_{t−l}) + ε_{t+h},   h = 1..12
```

- Sai số chuẩn HAC (Newey–West, `maxlags = h + 1`); **khoảng tin cậy 90%** = `β_h ± 1,645·se`.
- Phản ứng với cú sốc độ lớn `s` = `s·β_h` (tuyến tính; khoảng tin cậy nhân cùng `s`).
- **Không đủ dữ liệu thì nói thẳng** (T-4): nếu hồi quy ở `h = 1` có **dưới 60 quan sát** thì không ước lượng, hiện "Chưa đủ dữ liệu (có N tháng, cần ≥ 60)".
- Khoảng tin cậy chứa 0 thì gắn nhãn "**không phân biệt được với 0**".
- Tính toán ở backend Python (`statsmodels`); web chỉ hiển thị.

**Giao diện** `/kich-ban/` (có link từ trang tổng quan):
- Chọn cú sốc, nhập độ lớn (mặc định: Brent +20%, UST10Y +0,5 điểm %, USD +5%), bấm "Giả lập".
- Mỗi biến kết quả một bảng: tháng 1…12, phản ứng ước lượng và khoảng tin cậy (`+8,02 điểm % [7,85; 8,19]`), nhãn "không phân biệt được với 0" khi cần.
- Mỗi bảng ghi **mẫu đã dùng** (`Mẫu: 03/2009–08/2026 · 208 quan sát`) và **nguồn** của chuỗi.
- Dòng nhắc cố định: "Suy luận theo kịch bản từ quan hệ lịch sử, **không phải dự báo**."

**Không làm:** biểu đồ (bảng trước), nhiều cú sốc cùng lúc, cú sốc GPR/chính sách thương mại, tỷ giá và tín dụng (chờ connector NHNN), VAR/BVAR.

## 3. Nối lịch sử CPI (có ghi nguồn)

**Phát hiện khi đối chiếu (2026-10-27):** chuỗi `CPI` của dautubenvung **không cùng định nghĩa theo thời gian**:
- Từ 2025: CPI tháng so cùng kỳ (01–03/2025 trùng khít với IMF; 09/2025 = 3,38% như GSO công bố).
- 2021–2024: phần lớn là CPI **bình quân từ đầu năm** so cùng kỳ (tháng 12 trùng đúng lạm phát bình quân cả năm: 2021 1,84; 2022 3,15; 2023 3,25; 2024 3,63), vài tháng không khớp cả hai cách hiểu.

Vì vậy:
1. Connector mới **`dbnomics`**: chuỗi `vn.cpi_yoy_imf` = IMF `CPI/M.VN.PCPI_PC_CP_A_PT` (CPI tháng, % so cùng kỳ năm trước), có từ 12/2002, **dừng ở 03/2025** → trạng thái `partial`, chỉ dùng làm lịch sử. Bản gốc: `IMF_CPI_M.VN.PCPI_PC_CP_A_PT.json`, nguyên văn phản hồi của `GET api.db.nomics.world/v22/series/IMF/CPI/M.VN.PCPI_PC_CP_A_PT?observations=1` (đọc `series.docs[0].period` dạng `YYYY-MM` và `value`, bỏ `"NA"`).
2. Chuỗi mô hình `vn.cpi_yoy_long` (tính lúc ước lượng, không lưu như một nguồn): **IMF cho các tháng ≤ tháng cuối của IMF; dautubenvung cho các tháng sau đó**.
3. **Điều kiện nối:** ở 3 tháng cuối của IMF mà cả hai nguồn đều có, chênh lệch tuyệt đối lớn nhất **≤ 0,1 điểm %**. Không đạt thì **không nối**, biến CPI hiện "Chưa nối được lịch sử CPI: lệch tối đa X điểm % ở đoạn trùng" và không ước lượng.
4. Bảng CPI ghi nguồn từng đoạn: `Nguồn: IMF qua DBnomics (12/2002–03/2025) + dautubenvung.vn (04/2025–09/2026)`.
5. Registry: ghi lại định nghĩa thật của `vn.cpi_yoy` (trường `definition`), trạng thái `partial`. Thẻ CPI trên bảng tổng quan **không đổi** (các tháng gần đây cùng định nghĩa).

## 4. Tiêu chí nghiệm thu

Kiểm bằng `tests/journeys/test_scenario_simulation.py`. Dữ liệu tổng hợp sinh **có quan hệ biết trước** (seed cố định): tăng trưởng xuất khẩu so cùng kỳ `g_t = 5 + 0,4·x_{t−1} + u_t`, `x_t` = thay đổi giá dầu (độ lệch chuẩn 6%), `u_t` độ lệch chuẩn 0,5.

1. **Ước lượng đúng quan hệ:** chọn Brent +20% → phản ứng của xuất khẩu ở tháng 1 trong khoảng `8 ± 0,5` điểm %, không có nhãn "không phân biệt được với 0"; bảng ghi mẫu và số quan sát ≥ 60.
2. **Tuyến tính theo độ lớn:** Brent +10% cho phản ứng tháng 1 đúng bằng một nửa của +20%.
3. **Nối CPI có ghi nguồn:** IMF (12/2002–03/2025) và dautubenvung (từ 01/2021, khớp nhau ở 01–03/2025) → bảng CPI có kết quả và ghi `IMF qua DBnomics (12/2002–03/2025) + dautubenvung.vn (04/2025–09/2026)`.
4. **Không nối khi lệch:** đoạn trùng lệch 0,5 điểm % → bảng CPI hiện "Chưa nối được lịch sử CPI", không có số.
5. **Thiếu dữ liệu:** VN-Index chỉ có 30 tháng → "Chưa đủ dữ liệu", "cần ≥ 60", không có số.
6. Trang có dòng "không phải dự báo".

Ngoài journey: test đơn vị cho biến đổi chuỗi (tháng hoá chuỗi ngày, tăng trưởng so cùng kỳ), ước lượng LP trên dữ liệu có hệ số biết trước, quy tắc nối CPI, connector `dbnomics`; các gate chung của Proofline.

## 5. Hợp đồng giao diện (cho journey)

- `select[data-testid=shock]` với giá trị `global.brent`, `us.ust10y`, `us.usd_broad`; `input[data-testid=shock-size]`; `button[data-testid=run]`.
- `data-testid=disclaimer`.
- Mỗi biến kết quả: `data-testid=response-<series_id>`, bên trong `data-testid=sample` (mẫu, số quan sát, nguồn) và hoặc `data-testid=insufficient` (lý do), hoặc các dòng `data-testid=h-<n>` (n = 1…12) có thuộc tính số `data-estimate`, `data-lower`, `data-upper`, `data-n` (số quan sát) và phần tử `data-testid=zero` khi khoảng tin cậy chứa 0.
- API: `GET /api/scenario?shock=<series_id>&size=<số>`.

## 6. Quyết định của chủ dự án

- 2026-10-27: 3 cú sốc, 5 biến kết quả, local projections kèm khoảng tin cậy 90%, nối lịch sử CPI từ IMF có ghi nguồn.
- 2026-10-27: duyệt spec và acceptance journey v1; đồng ý thêm dependency `statsmodels`.
