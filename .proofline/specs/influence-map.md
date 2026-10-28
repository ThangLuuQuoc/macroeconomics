# Spec (nháp): Bản đồ ảnh hưởng dạng bong bóng

> Tính năng thứ bảy, **làm sau `synthetic-data`** (journey chạy trên dữ liệu giả lập). Trạng thái: **chờ duyệt** spec và acceptance journey (`tests/journeys/test_influence_map.py`, 2026-10-28).
> Liên quan: [`synthetic-data.md`](synthetic-data.md), [`scenario-simulation.md`](scenario-simulation.md), [`backtest.md`](backtest.md), [`multi-shock-model.md`](multi-shock-model.md).

## 1. Vấn đề

Các trang hiện có trả lời từng câu hỏi riêng ("dầu tăng 20% thì CPI ra sao", "mô hình từng đoán đúng tới đâu"). Người dùng chưa có một chỗ nhìn **một lần** để thấy: trong 12 tháng qua, những yếu tố nào đang **đẩy lên** hay **kéo xuống** kinh tế Việt Nam (hoặc VN-Index, xuất khẩu, CPI…), yếu tố nào mạnh nhất, và yếu tố nào mô hình **chưa chắc**.

## 2. Phạm vi

**Trang** `/anh-huong/` (link từ trang tổng quan và trang giả lập).

**Bong bóng trung tâm** — một biến kết quả, chọn được trong danh mục biến kết quả (GDP, xuất khẩu, IIP, PMI, CPI, VN-Index). Mặc định **"Kinh tế Việt Nam" (GDP so cùng kỳ, `vn.gdp_yoy`)** nếu có dữ liệu; chưa có (chế độ số thật hiện nay) thì VN-Index. Hiện **thay đổi thực tế trong 12 tháng** tính tới tháng đang xem (`y_m − y_{m−12}`, cùng đơn vị với trang giả lập) và mức hiện tại.

**Bong bóng xung quanh** — mọi yếu tố trong danh mục `SHOCKS` **có dữ liệu** ở database đang xem:
- ngoài nước: dầu Brent, lợi suất Mỹ 10 năm, USD rộng, cầu thế giới;
- trong nước: lãi suất điều hành NHNN, tỷ giá USD/VND, FDI giải ngân, tăng trưởng tín dụng, giải ngân đầu tư công.

Trên dữ liệu giả lập `baseline` có đủ 9 yếu tố; ở chế độ số thật hiện chỉ có 3 yếu tố ngoài nước đầu, các yếu tố còn lại liệt kê một dòng "Chưa có dữ liệu thật: …" (như `synthetic-data` mục 2.2). Vị trí **cố định** quanh trung tâm theo thứ tự trong danh mục — ngoài nước nửa trên, trong nước nửa dưới, có nhãn nhóm — không xáo trộn mỗi lần tải, để người dùng nhớ được chỗ. Bong bóng chọn làm trung tâm thì không hiện ở vòng ngoài.

Với tháng đang xem `m` và yếu tố `s`:

1. **Diễn biến của chính yếu tố:** thay đổi trong 12 tháng theo đơn vị cú sốc, `Σ_{t=m−11..m} x_t` (vd `Brent +15%` là tổng thay đổi log %, `Lãi suất +0,5 điểm %`), hiện bằng mũi tên ▲/▼ và con số.
2. **Đóng góp ước lượng vào trung tâm:** `đóng góp = Σ_{t=m−11..m−1} β_{m−t}·x_t` — cùng công thức với trang kiểm chứng (mốc cắt `m − 12`, tầm 1..11; cú sốc của chính tháng `m` chưa kịp tác động vì mô hình không có tầm 0), β là phản ứng của trang giả lập với cú sốc 1 đơn vị (ước lượng riêng từng yếu tố trên toàn bộ dữ liệu).
3. **Màu theo tác động lên trung tâm, không theo hướng của yếu tố:**
   - đóng góp > 0: **xanh dương**, chữ "đẩy lên";
   - đóng góp < 0: **cam**, chữ "kéo xuống";
   - **chưa chắc** — khoảng tin cậy 90% của phản ứng cộng dồn tại tầm 12 chứa 0 (`includes_zero` của trang giả lập): màu xám nhạt, viền đứt, chữ "chưa chắc", vẫn hiện con số.
   - Không dùng xanh lá/đỏ: khó phân biệt với người mù màu đỏ-xanh, và ở chứng khoán Việt Nam xanh/đỏ đã mang nghĩa giá tăng/giảm, dễ lẫn với hướng của chính yếu tố. Màu luôn đi kèm chữ và dấu +/−.
4. **Kích thước:** diện tích tỷ lệ với `|đóng góp|`, cùng thang cho mọi bong bóng trên trang; có bán kính tối thiểu để vẫn bấm được.
5. **Đường nối** từ bong bóng tới trung tâm: độ đậm theo `|β|` chuẩn hoá (phản ứng cộng dồn tại tầm 12 với một cú sốc độ lớn mặc định).
6. **Không cộng các đóng góp** ở v1: mỗi yếu tố ước lượng riêng nên tổng có thể đếm trùng (càng dễ xảy ra khi có cả yếu tố trong nước, vốn liên quan nhau). Trang ghi rõ: "Ảnh hưởng riêng của từng yếu tố, không cộng lại được." Khi `multi-shock-model` thay v1, trang thêm "phần mô hình giải thích" và "phần chưa giải thích" (spec riêng).

**Bảng xếp hạng** bên cạnh: các yếu tố xếp theo `|đóng góp|` giảm dần, thanh ngang hai phía (xanh dương sang phải, cam sang trái) — vì mắt người so diện tích hình tròn kém.

**Tương tác:**

- **Chọn tháng** (mặc định tháng mới nhất có dữ liệu của trung tâm; trên dữ liệu giả lập có thể tới 12/2036): xem lại hoặc xem "tương lai giả lập". Hệ số vẫn ước lượng trên toàn bộ dữ liệu (ghi rõ dưới thanh chọn: "nhìn lại bằng mô hình hôm nay, không phải dự báo lúc đó").
- **Bấm một bong bóng:** mở khung giả lập — thanh trượt độ lớn cú sốc (mặc định như trang giả lập), trung tâm hiện **phản ứng dự kiến sau 12 tháng** kèm khoảng tin cậy; số lấy từ `GET /api/scenario`, khớp với trang giả lập.
- **Trỏ chuột / chạm vào bong bóng:** β, khoảng tin cậy, số quan sát, nguồn số liệu.

**Thiếu dữ liệu:** trung tâm không đủ dữ liệu thì cả trang báo "Chưa đủ dữ liệu cho <biến>" và không vẽ bong bóng; một yếu tố có dữ liệu nhưng không đủ để ước lượng thì bong bóng của nó hiện "thiếu dữ liệu", không màu, không kích thước.

**Kỹ thuật:** tính toán ở backend (T-1), `GET /api/influence?center=<series_id>&month=YYYY-MM`, đọc database theo chế độ Thật/Giả lập của `synthetic-data`; vẽ bằng SVG thuần trong Next.js, bố cục hướng tâm cố định (không dùng mô phỏng lực); dùng được ở bề ngang điện thoại (bong bóng thu nhỏ, bảng xếp hạng xuống dưới); dải "DỮ LIỆU GIẢ LẬP" hiện như mọi trang.

**Không làm:** đường ảnh hưởng giữa các yếu tố với nhau (vd lãi suất → tín dụng); chuỗi ảnh hưởng nhiều tầng; hoạt ảnh chạy theo thời gian; khoảng tin cậy riêng cho phần đóng góp; tự giải thích bằng lời "vì sao".

## 3. Tiêu chí nghiệm thu dự kiến (chốt khi viết journey)

Kiểm bằng `tests/journeys/test_influence_map.py` trên kịch bản giả lập `influence-demo` (`backend/macro/synthetic/scenarios/influence-demo.yaml`, viết cùng journey), gồm đủ 9 yếu tố và GDP như `baseline`, từ 01/1990, gài sẵn với trung tâm VN-Index:

- `vn.vnindex ← global.brent`, β = −0,5; Brent **tăng** mạnh (+40, 08/2036);
- `vn.vnindex ← us.usd_broad`, β = −1,3; USD **giảm** mạnh (−12, 10/2036);
- `vn.vnindex ← vn.credit_growth`, β = 3; tín dụng **tăng** mạnh (+5, 09/2036);
- `us.ust10y` không gài quan hệ với VN-Index;
- không có dữ liệu CPI.

Mỗi cú sốc lớn ở một tháng riêng: cùng tháng thì mô hình từng cặp gán cả bước nhảy của VN-Index cho từng yếu tố (đếm trùng) và ra sai dấu. Đã đo trước khi duyệt, với chính mô hình đang chạy, trên 60 seed: Brent "kéo xuống" 60/60, USD "đẩy lên" 59/60, tín dụng "đẩy lên" 58/60, lợi suất Mỹ "chưa chắc" 53/60 (trần ~90% vì là khoảng tin cậy 90%); seed 42 của kịch bản đạt cả bốn. Journey đọc dấu β từ tệp kịch bản và khẳng định chúng, nên sửa kịch bản làm đổi ý nghĩa thì journey báo.

1. Bật Giả lập, chọn `influence-demo`, từ trang tổng quan vào được `/anh-huong/`; có dải "DỮ LIỆU GIẢ LẬP"; trung tâm mặc định là "Kinh tế Việt Nam" (GDP), vòng ngoài có đủ 9 yếu tố, chia nhóm ngoài nước / trong nước.
2. Đổi trung tâm sang VN-Index:
   - **Brent:** mũi tên ▲, bong bóng **cam** "kéo xuống", đóng góp âm.
   - **USD:** mũi tên ▼ nhưng bong bóng **xanh dương** "đẩy lên", đóng góp dương — màu theo tác động, không theo hướng.
   - **Tín dụng:** ▲, xanh dương "đẩy lên".
   - **Lợi suất Mỹ:** "chưa chắc".
3. Bong bóng có `|đóng góp|` lớn hơn thì bán kính lớn hơn; bảng xếp hạng đúng thứ tự `|đóng góp|`.
4. Đóng góp của Brent trên trang khớp với công thức ở mục 2 tính lại từ `GET /api/scenario` và dữ liệu (sai lệch ≤ 0,01).
5. Bấm Brent, đặt độ lớn 10%: phản ứng sau 12 tháng (ước lượng và khoảng tin cậy) bằng đúng số của `GET /api/scenario` với cùng cú sốc và độ lớn.
6. Chọn tháng sớm hơn: các con số đổi theo tháng đó; chọn một tháng năm 2030: GDP trung tâm trong [9%, 15%].
7. Đổi trung tâm sang CPI: "Chưa đủ dữ liệu cho CPI", không có bong bóng.
8. **Số thật** (bộ số nạp sẵn: PMI, IIP, Brent): trung tâm mặc định VN-Index, báo "Chưa đủ dữ liệu cho VN-Index"; có dòng "Chưa có dữ liệu thật: …"; đổi trung tâm sang PMI thì có đúng 3 bong bóng (3 yếu tố gốc), lợi suất Mỹ "thiếu dữ liệu", Brent có số.
9. Bề ngang 375 px: không cuộn ngang, đủ 9 bong bóng và bảng xếp hạng.

## 4. Hợp đồng giao diện

- Link `Bản đồ ảnh hưởng` trên trang tổng quan và trang giả lập.
- `data-testid=center-select` (chọn trung tâm), `data-testid=month-select` (giá trị `YYYY-MM`).
- `data-testid=center` có `data-series`, `data-change`, `data-level`.
- Mỗi yếu tố: `data-testid=bubble-<series_id>` có `data-scope` (`global` | `domestic`), `data-contribution`, `data-shock-change`, `data-effect` (`up` | `down` | `uncertain` | `missing`), `data-radius`.
- `data-testid=ranking`, các dòng `data-testid=rank-<series_id>` theo thứ tự.
- Khung giả lập: `data-testid=simulate-<series_id>`, ô độ lớn `data-testid=shock-size`, kết quả `data-testid=simulated-response` có `data-size`, `data-estimate`, `data-lower`, `data-upper` (tầm 12).
- `data-testid=not-additive`: dòng "Ảnh hưởng riêng của từng yếu tố, không cộng lại được."
- `data-testid=insufficient` khi trung tâm không đủ dữ liệu; `data-testid=no-real-data` (từ `synthetic-data`).
- API: `GET /api/influence?center=<series_id>&month=YYYY-MM`.

## 5. Quyết định của chủ dự án

- 2026-10-28: làm màn hình bong bóng sau `synthetic-data`; màu thể hiện tác động lên trung tâm, độ lớn và đường nối lấy từ mô hình; v1 dùng hệ số từng cặp và không cộng dồn.
- 2026-10-28, câu hỏi mở:
  1. "Kinh tế Việt Nam" ở trung tâm là **GDP theo tháng giả lập**: từ 2026 tới 10 năm sau tăng trưởng luôn trong 9%–15% (cách sinh ở `synthetic-data` mục 2.2).
  2. **Thêm đủ các yếu tố** (cầu thế giới, lãi suất điều hành, tỷ giá, FDI, tín dụng, đầu tư công) vì đang dùng dữ liệu giả lập; khi số thật chưa có thì yếu tố đó không hiện.
  3. Nhãn "chưa chắc" theo khoảng tin cậy tại tầm 12.
  4. Cặp màu xanh dương / cam.
