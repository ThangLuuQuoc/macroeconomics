# Spec: Kiểm chứng lịch sử (backtest) của mô hình giả lập

> Tính năng thứ tư của `macroeconomics`. Trạng thái: **đã duyệt** (chủ dự án, 2026-10-27).
> Liên quan: [`scenario-simulation.md`](scenario-simulation.md); nhận định 2026-10-27 (phép thử năm 2022: mô hình hiện tại không tái hiện được điều đã xảy ra).

## 1. Vấn đề

Trang giả lập cho ra con số và khoảng tin cậy, nhưng người dùng không biết **mô hình từng đoán đúng tới đâu**. Phép thử tay với năm 2022 cho thấy mô hình bỏ sót gần hết cú giảm 40 điểm % của tăng trưởng xuất khẩu. App cần tự cho thấy **thành tích lịch sử** của mô hình, để người dùng biết khi nào nên tin, và để các cải tiến sau (mô hình nhiều cú sốc, cầu toàn cầu) có thước đo khách quan.

## 2. Phạm vi

**Cách kiểm (rolling origin, không nhìn trước):**

1. **Mốc cắt** `c`: mọi tháng 12 sao cho (a) ước lượng trên dữ liệu ≤ `c` có **≥ 60 quan sát ở mọi tầm h = 1..12**, và (b) có số thực tế ở `c + 12`.
2. Tại mỗi mốc: ước lượng mô hình **chỉ bằng dữ liệu ≤ `c`**, đưa vào các cú sốc **thật** của các tháng `c+1 … c+11`, tính **thay đổi dự đoán** `Δŷ = ŷ_{c+12} − y_c`, so với **thay đổi thực tế** `Δy = y_{c+12} − y_c`.
3. **Mô hình v1** (mô hình đang dùng ở trang giả lập): mỗi cú sốc ước lượng riêng, dự đoán là **tổng đóng góp của từng cú sốc**: `Δŷ = Σ_cú sốc Σ_{t=c+1..c+11} β_{c+12−t}·x_t`. Ghi rõ trên trang: cách cộng này có thể đếm trùng khi các cú sốc liên quan nhau. Cú sốc thiếu dữ liệu ở mốc nào thì không góp và được liệt kê là "thiếu".
4. **Mốc so sánh "không đổi"**: `Δŷ = 0` (đoán biến giữ nguyên sau 12 tháng).
5. **Chỉ số tổng hợp cho mỗi biến kết quả:**
   - MAE của mô hình và MAE của "không đổi"; **tỷ lệ** `MAE mô hình / MAE "không đổi"`;
   - tỷ lệ **đoán đúng hướng** (dấu của `Δŷ` trùng dấu của `Δy`);
   - **kết luận**: tỷ lệ MAE **≤ 0,8** thì "Tốt hơn đoán 'không đổi'", ngược lại "Không tốt hơn đoán 'không đổi'".
6. Biến kết quả và cú sốc: như trang giả lập (5 biến, 3 cú sốc; CPI dùng chuỗi nối IMF + dautubenvung). Không có mốc cắt nào hợp lệ thì "Chưa đủ dữ liệu để kiểm chứng", không có số.

**Giao diện** `/kiem-chung/` (link từ trang tổng quan và trang giả lập):
- Mỗi biến kết quả một khối: kết luận, MAE hai bên, tỷ lệ, tỷ lệ đúng hướng, số mốc.
- Bảng các mốc: `12/2014 → 12/2015`, thay đổi thực tế, thay đổi dự đoán, sai số; cú sốc bị thiếu (nếu có).
- Dòng giải thích cách kiểm và giới hạn của mô hình v1.
- Tính toán ở backend, cùng các hàm của trang giả lập (T-1); thời gian trả lời mục tiêu ≤ 10 giây.

**Không làm:** chọn mốc tuỳ ý, tầm khác 12 tháng, biểu đồ, mô hình mới (spec `multi-shock-model`).

## 3. Tiêu chí nghiệm thu

Kiểm bằng `tests/journeys/test_backtest.py`. Dữ liệu tổng hợp (seed cố định), chỉ có cú sốc Brent (`x_t` độ lệch chuẩn 6%):
- PMI: `y_t = y_{t−1} + 0,2·x_{t−1} + u_t`, `u_t` độ lệch chuẩn 0,3 (quan hệ thật, bền).
- IIP: `8 + nhiễu` độ lệch chuẩn 2 (không liên quan cú sốc).

Đã chạy thử thiết kế: PMI cho tỷ lệ MAE 0,46; IIP 0,95.

1. Từ trang tổng quan vào được trang kiểm chứng.
2. **PMI:** kết luận "Tốt hơn đoán 'không đổi'"; tỷ lệ MAE ≤ 0,8; có ít nhất 10 mốc, mỗi mốc có thực tế, dự đoán, sai số; mốc đầu tiên không sớm hơn khi đủ 60 quan sát.
3. **IIP:** kết luận "Không tốt hơn đoán 'không đổi'".
4. **CPI** (không có dữ liệu): "Chưa đủ dữ liệu để kiểm chứng", không có số.
5. Trang ghi rõ lợi suất Mỹ và USD là cú sốc **thiếu** (không có dữ liệu).

## 4. Hợp đồng giao diện

- Link `Kiểm chứng lịch sử` trên trang tổng quan.
- Mỗi biến: `data-testid=backtest-<series_id>`; bên trong `data-testid=verdict`, `data-testid=summary` có thuộc tính số `data-mae-model`, `data-mae-naive`, `data-ratio`, `data-hit-rate`, `data-episodes`; các dòng `data-testid=episode-<YYYY-MM>` (theo mốc cắt) có `data-actual`, `data-predicted`; hoặc `data-testid=insufficient`.
- `data-testid=missing-shocks` liệt kê cú sốc thiếu dữ liệu.
- API: `GET /api/backtest`.

## 5. Quyết định của chủ dự án

- 2026-10-27: làm kiểm chứng lịch sử trước, rồi mô hình nhiều cú sốc và cầu toàn cầu (spec `multi-shock-model`).
- 2026-10-27: duyệt spec và acceptance journey v1, ngưỡng kết luận 0,8.
