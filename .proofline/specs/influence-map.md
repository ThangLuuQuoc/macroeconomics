# Spec (nháp): Bản đồ ảnh hưởng dạng bong bóng

> Tính năng thứ bảy, **làm sau `synthetic-data`** (journey chạy trên dữ liệu giả lập). Trạng thái: **nháp**, chưa có acceptance journey; journey viết sau khi chốt các câu hỏi ở mục 6.
> Liên quan: [`synthetic-data.md`](synthetic-data.md), [`scenario-simulation.md`](scenario-simulation.md), [`backtest.md`](backtest.md), [`multi-shock-model.md`](multi-shock-model.md).

## 1. Vấn đề

Các trang hiện có trả lời từng câu hỏi riêng ("dầu tăng 20% thì CPI ra sao", "mô hình từng đoán đúng tới đâu"). Người dùng chưa có một chỗ nhìn **một lần** để thấy: trong 12 tháng qua, những yếu tố bên ngoài nào đang **đẩy lên** hay **kéo xuống** VN-Index (hoặc xuất khẩu, CPI…), yếu tố nào mạnh nhất, và yếu tố nào mô hình **chưa chắc**.

## 2. Phạm vi

**Trang** `/anh-huong/` (link từ trang tổng quan và trang giả lập).

**Bong bóng trung tâm** — một biến kết quả, chọn được trong 5 biến của trang giả lập (xuất khẩu, IIP, PMI, CPI, VN-Index); mặc định VN-Index. Hiện **thay đổi thực tế trong 12 tháng** tính tới tháng đang xem (`y_m − y_{m−12}`, cùng đơn vị với trang giả lập).

**Bong bóng xung quanh** — mỗi cú sốc mà mô hình có (hiện 3: dầu Brent, lợi suất Mỹ 10 năm, USD rộng; thêm cầu toàn cầu khi `multi-shock-model` xong). Vị trí cố định quanh trung tâm (không xáo trộn mỗi lần tải), để người dùng nhớ được chỗ.

Với tháng đang xem `m` và cú sốc `s`:

1. **Diễn biến của chính cú sốc:** thay đổi trong 12 tháng (vd `Brent +15%`), hiện bằng mũi tên ▲/▼ và con số.
2. **Đóng góp ước lượng vào trung tâm:** `đóng góp = Σ_{t=m−11..m} β_{m−t}·x_t` — cùng công thức, cùng hàm ước lượng với trang kiểm chứng (mô hình v1, ước lượng riêng từng cú sốc trên toàn bộ dữ liệu).
3. **Màu theo tác động lên trung tâm, không theo hướng của cú sốc:**
   - đóng góp > 0: **xanh dương**, chữ "đẩy lên";
   - đóng góp < 0: **cam**, chữ "kéo xuống";
   - **chưa chắc** (khoảng tin cậy 90% của phản ứng cộng dồn tại tầm 12 chứa 0, như `includes_zero` của trang giả lập): màu xám nhạt, viền đứt, chữ "chưa chắc", vẫn hiện con số.
   - Màu luôn đi kèm chữ và dấu +/−, không chỉ dựa vào màu (người mù màu).
4. **Kích thước:** diện tích tỷ lệ với `|đóng góp|`, cùng thang cho mọi bong bóng trên trang; có bán kính tối thiểu để vẫn bấm được.
5. **Đường nối** từ bong bóng tới trung tâm: độ đậm theo `|β|` chuẩn hoá (phản ứng cộng dồn tại tầm 12 với một cú sốc độ lớn mặc định).
6. **Không cộng các đóng góp** ở v1: mỗi cú sốc ước lượng riêng nên tổng có thể đếm trùng. Trang ghi rõ: "Ảnh hưởng riêng của từng yếu tố, không cộng lại được." Khi `multi-shock-model` thay v1, trang thêm "phần mô hình giải thích" và "phần chưa giải thích" (spec riêng).

**Bảng xếp hạng** bên cạnh: các cú sốc xếp theo `|đóng góp|` giảm dần, thanh ngang hai phía (xanh dương sang phải, cam sang trái) — vì mắt người so diện tích hình tròn kém.

**Tương tác:**

- **Chọn tháng** (mặc định tháng mới nhất có dữ liệu của trung tâm): xem lại một giai đoạn, vd 12/2022. Hệ số vẫn ước lượng trên toàn bộ dữ liệu (ghi rõ dưới thanh chọn: "nhìn lại bằng mô hình hôm nay, không phải dự báo lúc đó").
- **Bấm một bong bóng:** mở khung giả lập — thanh trượt độ lớn cú sốc (mặc định như trang giả lập), trung tâm hiện **phản ứng dự kiến sau 12 tháng** kèm khoảng tin cậy; số lấy từ `GET /api/scenario`, khớp với trang giả lập.
- **Trỏ chuột / chạm vào bong bóng:** β, khoảng tin cậy, số quan sát, nguồn số liệu.

**Thiếu dữ liệu:** trung tâm không đủ dữ liệu thì cả trang báo "Chưa đủ dữ liệu cho <biến>" và không vẽ bong bóng; một cú sốc không đủ dữ liệu thì bong bóng của nó hiện "thiếu dữ liệu", không màu, không kích thước.

**Kỹ thuật:** tính toán ở backend (T-1), `GET /api/influence?center=<series_id>&month=YYYY-MM`; vẽ bằng SVG thuần trong Next.js, bố cục hướng tâm cố định (không dùng mô phỏng lực); dùng được ở bề ngang điện thoại (bong bóng xếp lại, bảng xếp hạng xuống dưới); dải "DỮ LIỆU GIẢ LẬP" của `synthetic-data` hiện như mọi trang.

**Không làm:** ảnh hưởng qua lại giữa các biến trong nước (vd CPI → VN-Index); chuỗi ảnh hưởng nhiều tầng; hoạt ảnh chạy theo thời gian; tự giải thích bằng lời "vì sao".

## 3. Tiêu chí nghiệm thu dự kiến (chốt khi viết journey)

Kiểm bằng `tests/journeys/test_influence_map.py` trên kịch bản giả lập `influence-demo` (thêm vào `backend/macro/synthetic/scenarios/`), gài sẵn:

- `vn.vnindex ← global.brent`, β âm; Brent **tăng** trong 12 tháng cuối;
- `vn.vnindex ← us.usd_broad`, β âm; USD **giảm** trong 12 tháng cuối;
- `us.ust10y` không gài quan hệ với VN-Index;
- không có dữ liệu CPI.

1. Từ trang tổng quan vào được `/anh-huong/`; trung tâm mặc định VN-Index, có dải "DỮ LIỆU GIẢ LẬP".
2. **Brent:** mũi tên ▲, bong bóng **cam** "kéo xuống", đóng góp âm.
3. **USD:** mũi tên ▼ nhưng bong bóng **xanh dương** "đẩy lên", đóng góp dương — màu theo tác động, không theo hướng.
4. **Lợi suất Mỹ:** "chưa chắc".
5. Bong bóng có `|đóng góp|` lớn hơn thì bán kính lớn hơn; bảng xếp hạng đúng thứ tự `|đóng góp|`.
6. Đóng góp của Brent trên trang khớp với công thức ở mục 2 tính lại từ `GET /api/scenario` và dữ liệu (sai lệch ≤ 0,01).
7. Bấm Brent, kéo độ lớn tới +20%: trung tâm hiện phản ứng sau 12 tháng bằng đúng số của trang giả lập với cùng cú sốc và độ lớn.
8. Chọn tháng sớm hơn: các con số đổi theo tháng đó.
9. Đổi trung tâm sang CPI: "Chưa đủ dữ liệu cho CPI", không có bong bóng.
10. Bề ngang 375 px: không cuộn ngang, đủ 3 bong bóng và bảng xếp hạng.

## 4. Hợp đồng giao diện

- Link `Bản đồ ảnh hưởng` trên trang tổng quan và trang giả lập.
- `data-testid=center-select` (chọn trung tâm), `data-testid=month-select`.
- `data-testid=center` có `data-series`, `data-change`.
- Mỗi cú sốc: `data-testid=bubble-<series_id>` có `data-contribution`, `data-shock-change`, `data-effect` (`up` | `down` | `uncertain` | `missing`), `data-radius`.
- `data-testid=ranking`, các dòng `data-testid=rank-<series_id>` theo thứ tự.
- Khung giả lập: `data-testid=simulate-<series_id>`, thanh trượt `data-testid=shock-size`, kết quả `data-testid=simulated-response` có `data-estimate`, `data-lower`, `data-upper`.
- `data-testid=insufficient` khi trung tâm không đủ dữ liệu.
- API: `GET /api/influence?center=<series_id>&month=YYYY-MM`.

## 5. Quyết định của chủ dự án

- 2026-10-28: làm màn hình bong bóng sau `synthetic-data`; màu thể hiện tác động lên trung tâm, độ lớn và đường nối lấy từ mô hình; v1 dùng hệ số từng cặp và không cộng dồn.

## 6. Câu hỏi mở

1. "Kinh tế Việt Nam" làm trung tâm: hiện chưa có GDP theo tháng. Dùng IIP làm đại diện, hay thêm GDP theo quý (nguồn nào?) trong một spec riêng?
2. Chỉ 3 bong bóng khá thưa. Chấp nhận cho v1, hay đợi `multi-shock-model` (thêm cầu toàn cầu) rồi mới làm?
3. Đặt nhãn "chưa chắc" theo khoảng tin cậy tại tầm 12 có đủ không, hay cần khoảng tin cậy của chính phần đóng góp (phải tính thêm, phức tạp hơn)?
4. Cặp màu xanh dương/cam thay cho xanh lá/đỏ: đồng ý không? (Xanh lá/đỏ khó phân biệt với người mù màu đỏ-xanh, và ở chứng khoán Việt Nam xanh/đỏ đã mang nghĩa giá tăng/giảm, dễ lẫn với hướng của chính cú sốc.)
