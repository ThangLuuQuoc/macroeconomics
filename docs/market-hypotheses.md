# Giả thuyết về thị trường

> Kho tri thức nghiệp vụ của `macroeconomics`: các quy luật **được nghĩ là đúng** về cách thị trường và nền kinh tế phản ứng. Mỗi giả thuyết là một **phát biểu có thể kiểm chứng**, không phải quy tắc gắn cứng vào mô hình.
>
> **Quy tắc:** một giả thuyết chỉ được dùng trong trang giả lập khi trang kiểm chứng lịch sử (`/kiem-chung/`) cho thấy dùng nó **làm giảm sai số** so với không dùng. Số sự kiện thường ít, nên rất dễ "thấy quy luật" từ vài trường hợp; vì vậy luôn ghi số trường hợp và khoảng tin cậy.

## Trạng thái

| Trạng thái | Nghĩa |
| :--- | :--- |
| `chưa kiểm` | Mới ghi nhận, chưa có cách đo hoặc chưa chạy kiểm chứng |
| `đang kiểm` | Đã có cách đo trong một spec đang làm |
| `được ủng hộ` | Kiểm chứng cho thấy dùng giả thuyết làm giảm sai số; ghi rõ biến, tầm, số trường hợp |
| `bị bác bỏ` | Kiểm chứng không ủng hộ; giữ lại để không thử lại vô ích |
| `chưa đủ dữ liệu` | Không đủ trường hợp để kết luận |

## Danh sách

### H-1: Độ bất ngờ quyết định phản ứng
- **Phát biểu:** thị trường phản ứng với **phần bất ngờ** của một cú sốc, không phải toàn bộ thay đổi. Thay đổi đã được dự đoán trước (vd Fed tăng lãi suất đúng như kỳ vọng) tác động ít hơn nhiều so với thay đổi bất ngờ cùng độ lớn.
- **Cách đo:** tách cú sốc thành phần dự đoán được (mô hình tự hồi quy đơn giản trên chính chuỗi cú sốc, chỉ dùng quá khứ) và phần bất ngờ (phần dư); ước lượng phản ứng với từng phần. Về sau có thể dùng kỳ vọng của thị trường (hợp đồng tương lai lãi suất, giá dầu kỳ hạn) nếu có nguồn.
- **Áp dụng cho:** mọi biến, rõ nhất ở VN-Index và lãi suất.
- **Spec:** [`multi-shock-model`](../.proofline/specs/multi-shock-model.md) (lựa chọn A).
- **Trạng thái:** `đang kiểm`.
- **Nguồn:** chủ dự án, 2026-10-27.

### H-2: Lần đầu phản ứng mạnh hơn các lần lặp lại
- **Phát biểu:** cùng một loại cú sốc, **lần đầu** sau một thời gian dài yên ổn gây phản ứng mạnh hơn các lần sau, vì thị trường đã "quen" và đã định giá sẵn khả năng lặp lại (vd đợt công bố thuế quan đầu tiên so với các đợt sau).
- **Cách đo:**
  - Theo tháng: local projections phụ thuộc trạng thái, thêm tương tác `cú sốc × [là cú sốc lớn đầu tiên trong N tháng]` (cú sốc lớn = vượt 2 độ lệch chuẩn); so hệ số lần đầu với lần lặp lại.
  - Theo ngày, cho VN-Index: nghiên cứu sự kiện, so phản ứng ở các sự kiện được đánh dấu "lần đầu" với "lặp lại" cùng loại.
- **Áp dụng cho:** VN-Index (chính), các biến khác (phụ).
- **Spec:** [`multi-shock-model`](../.proofline/specs/multi-shock-model.md) (lựa chọn B), [`event-study`](../.proofline/specs/event-study.md).
- **Trạng thái:** `đang kiểm`.
- **Nguồn:** chủ dự án, 2026-10-27.

### H-3: Tin xấu tác động mạnh hơn tin tốt (bất đối xứng)
- **Phát biểu:** cú sốc bất lợi gây phản ứng lớn hơn cú sốc thuận lợi cùng độ lớn.
- **Cách đo:** tách cú sốc thành phần dương và phần âm trong hồi quy, so hai hệ số.
- **Trạng thái:** `chưa kiểm`.
- **Nguồn:** đề xuất bổ sung, 2026-10-27.

### H-4: Cú sốc rất lớn gây phản ứng hơn tỷ lệ (phi tuyến theo độ lớn)
- **Phát biểu:** phản ứng không tăng tuyến tính theo độ lớn; cú sốc vượt một ngưỡng gây phản ứng lớn hơn tỷ lệ (hoảng loạn, bán tháo).
- **Cách đo:** thêm số hạng bình phương hoặc biến ngưỡng của cú sốc.
- **Trạng thái:** `chưa kiểm`.
- **Nguồn:** đề xuất bổ sung, 2026-10-27.

## Thêm giả thuyết mới

Thêm một mục theo đúng mẫu trên (phát biểu, cách đo, áp dụng cho, spec, trạng thái, nguồn). Đổi trạng thái chỉ khi có kết quả kiểm chứng, và ghi lại kết quả đó (biến, tầm, số trường hợp, tỷ lệ sai số trước/sau).
