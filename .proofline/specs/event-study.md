# Spec (nháp): Sự kiện và phản ứng của VN-Index theo ngày

> Tính năng sau `multi-shock-model` (hoặc song song). Trạng thái: **nháp**, chưa có acceptance journey; journey viết khi bắt đầu.
> Liên quan: [`../../docs/market-hypotheses.md`](../../docs/market-hypotheses.md) (H-2, H-3), [`backtest.md`](backtest.md), [`market-cards.md`](market-cards.md).

## 1. Vấn đề

- Tâm lý thị trường (độ bất ngờ, "lần đầu mạnh hơn lần sau") thể hiện rõ nhất ở **giá tài sản trong vài phiên đến vài tuần**, không ở số liệu vĩ mô theo tháng.
- VN-Index theo tháng chỉ có 73 quan sát (từ 2020) nên trang giả lập và kiểm chứng đều "chưa đủ dữ liệu"; theo ngày thì có khoảng **1.600 phiên**.
- Chủ dự án muốn biết, với một loại sự kiện (vd công bố thuế quan, Fed đổi hướng, xung đột lớn), VN-Index thường phản ứng thế nào, và **lần đầu có mạnh hơn các lần lặp lại không** (H-2).

## 2. Phạm vi dự kiến

1. **Danh sách sự kiện, đánh dấu tay** (đúng phương án "đánh dấu sự kiện tay" ở phỏng vấn đầu):
   - Trường: ngày, loại sự kiện (chọn từ danh sách loại do chủ dự án định nghĩa), mô tả ngắn, nguồn (link), hướng kỳ vọng (xấu/tốt cho thị trường), **thứ tự** (lần đầu / lặp lại, tự tính theo loại: lần đầu = không có sự kiện cùng loại trong 180 ngày trước, có thể sửa tay).
   - Nhập trên một trang `/su-kien/` của app, lưu trong Postgres (bảng `events`), có lịch sử sửa.
2. **Nghiên cứu sự kiện (event study)** trên VN-Index theo ngày:
   - Lợi suất bất thường = lợi suất ngày của VN-Index trừ lợi suất "bình thường" (trung bình 120 phiên trước sự kiện, cách sự kiện 10 phiên để không lẫn).
   - Cửa sổ: từ 1 phiên trước tới 20 phiên sau; lợi suất bất thường **tích luỹ** (CAR) tại 1, 5, 10, 20 phiên.
   - Theo từng loại sự kiện: CAR trung bình kèm khoảng tin cậy 90%, **tách "lần đầu" và "lặp lại"**, ghi số sự kiện mỗi nhóm.
   - Dưới 3 sự kiện trong một nhóm thì hiện "Chưa đủ dữ liệu", không đưa ra số (T-4).
3. **Kết luận cho H-2:** "lần đầu" có CAR tuyệt đối lớn hơn "lặp lại" với khoảng tin cậy của chênh lệch không chứa 0 → cập nhật trạng thái H-2 trong danh sách giả thuyết (kèm số sự kiện); ngược lại ghi `bị bác bỏ` hoặc `chưa đủ dữ liệu`.

**Không làm:** tự thu thập và chấm tin bằng AI (để sau; phỏng vấn đầu đã chọn dùng chỉ số có sẵn trước), dữ liệu trong ngày, từng mã cổ phiếu.

## 3. Tiêu chí nghiệm thu dự kiến (chốt khi viết journey)

- Nhập một sự kiện trên trang, sự kiện cùng loại thứ hai trong 180 ngày được tự đánh dấu "lặp lại".
- Dữ liệu tổng hợp: VN-Index giảm 5% sau các sự kiện "lần đầu" và 2% sau "lặp lại" (cộng nhiễu, seed cố định) → trang hiện CAR hai nhóm đúng khoảng, chênh lệch có ý nghĩa, H-2 được đề xuất `được ủng hộ`; dữ liệu không có khác biệt → không đề xuất.
- Nhóm dưới 3 sự kiện → "Chưa đủ dữ liệu".

## 4. Câu hỏi mở

1. Danh sách loại sự kiện ban đầu: thuế quan / chính sách thương mại Mỹ; Fed đổi hướng lãi suất; xung đột quân sự lớn; NHNN điều chỉnh lãi suất điều hành; nâng hạng thị trường; khác?
2. Khoảng "lần đầu" (180 ngày) và cửa sổ (20 phiên): giữ mặc định?
3. Ai nhập sự kiện quá khứ (2020–2026) lần đầu: chủ dự án, hay app đề xuất danh sách từ lịch sử biến động lớn của VN-Index để chủ dự án xác nhận?
