# Phỏng vấn sản phẩm: macroeconomics

> Luồng A (khởi đầu từ ý tưởng), mức sẵn sàng R0. Phỏng vấn ngày 2026-10-27.
> Phần gu Tech Lead (10–15 câu theo docs/05 của Proofline) chưa hỏi.

## 1. Mục tiêu

Trực quan hoá và dự đoán sự phát triển của **kinh tế Việt Nam** dựa trên các yếu tố vĩ mô quan trọng, và **giả lập tác động** của các cú sốc bên ngoài (giá dầu, vàng, chiến tranh, chính sách thương mại…) lên **kinh tế và thị trường chứng khoán Việt Nam**.

- **Người dùng:** chỉ chủ dự án (công cụ cá nhân, không cần đăng nhập phức tạp).
- **Dữ liệu:** Việt Nam (GSO, Hải quan, NHNN, Bộ Tài chính…), Mỹ (FRED), toàn cầu (World Bank, IMF).
- **Chứng khoán:** đọc từ `stock_db` của openstock (**chỉ đọc**), không thu thập lại.

## 2. Thứ tự giá trị

1. **Bảng tổng quan** (tính năng đầu tiên): các chỉ số chính, giá trị mới nhất, thay đổi so với kỳ trước và cùng kỳ.
2. **Giả lập kịch bản:** chọn cú sốc (vd dầu +20%, Fed +0,5 điểm, xuất khẩu −10%) → xem tác động lên CPI, xuất khẩu, tỷ giá, VN-Index trong 3–12 tháng, **kèm khoảng tin cậy** và backtest. Là công cụ suy luận theo kịch bản, không phải dự đoán chắc chắn (dữ liệu Việt Nam ngắn, hay đổi phương pháp).
3. Nowcast GDP quý, dự báo dài hạn: sau.
4. **Tin tức:** giai đoạn đầu dùng các chỉ số định lượng có sẵn (GPR cho địa chính trị, EPU/TPU cho bất định chính sách thương mại, giá dầu/vàng); tự thu thập và chấm tin bằng AI để sau.

## 3. Yếu tố theo dõi (đề xuất ban đầu)

| Nhóm | Chỉ số | Tần suất | Nguồn |
| :--- | :--- | :--- | :--- |
| Tăng trưởng | GDP, IIP, bán lẻ hàng hoá & dịch vụ | Quý / tháng | GSO |
| Thương mại | Xuất khẩu, nhập khẩu, cán cân; theo mặt hàng và thị trường (Mỹ, Trung Quốc, EU) | Tháng | GSO, Hải quan |
| Vốn ngoại | FDI đăng ký và giải ngân | Tháng | Cục Đầu tư nước ngoài |
| Đơn hàng | PMI sản xuất Việt Nam (đơn hàng mới, đơn hàng xuất khẩu mới) | Tháng | S&P Global (chi tiết có thể phải trả phí) |
| Giá cả | CPI, lạm phát cơ bản | Tháng | GSO |
| Tiền tệ | Lãi suất điều hành, liên ngân hàng, tăng trưởng tín dụng, tỷ giá USD/VND | Ngày / tháng | NHNN |
| Tài khoá | Giải ngân đầu tư công | Tháng | Bộ Tài chính |
| Thị trường | VN-Index, thanh khoản, khối ngoại mua/bán ròng | Ngày | `stock_db` (openstock) |
| Bên ngoài | Brent, vàng, lãi suất Fed, lợi suất UST 10 năm, chỉ số USD | Ngày / tháng | FRED và nguồn giá vàng |
| Bên ngoài | Kinh tế Mỹ, Trung Quốc, EU; cước container | Tháng | FRED, World Bank, IMF, chỉ số cước |
| Rủi ro | Chỉ số GPR (địa chính trị), EPU/TPU (bất định chính sách) | Tháng / ngày | Công bố miễn phí |

## 4. Quyết định kỹ thuật

- **Stack:** Python (FastAPI, pandas, statsmodels) cho dữ liệu và mô hình; **Postgres** lưu chuỗi số liệu; **Next.js** cho giao diện.
- Đủ điều kiện cho gate của Proofline: test xuất JUnit (pytest, vitest), kịch bản người dùng bằng Playwright, app khởi chạy được để chạy journey.

## 5. Nguồn dữ liệu: adapter, dùng dautubenvung trước

**Quyết định (chủ dự án, 2026-10-27):** giai đoạn đầu lấy dữ liệu vĩ mô Việt Nam từ API nội bộ của **dautubenvung.vn** (`/api/data-vi-mo`, `/api/lai-suat-ngan-hang`, `/api/data-the-gioi`), **qua một adapter**; về sau dữ liệu sẽ nằm ngay trong openstock và chỉ cần đổi adapter. Đã biết: API không công khai, có thể đổi bất cứ lúc nào, một phần khoá sau gói trả phí; `robots.txt` của trang ghi `Content-Signal: search=yes, ai-train=no, use=reference`.

**Cách dùng cho nhẹ:** lấy theo lịch thưa (dữ liệu tháng/quý, vài lần mỗi ngày là đủ), lưu lại và đọc từ Postgres của app, không gọi API mỗi lần người dùng mở trang; chỉ dùng cá nhân, không phân phối lại; khi API đổi thì áp dụng nguyên tắc T-4 (giữ số cũ, báo rõ).

**Trang có** (mới nhất tới 09/2026): GDP danh nghĩa và thực theo ngành (quý, từ 2010); bán lẻ (tháng, từ 2004); CPI và các nhóm (tháng, **chỉ từ 2021**); xuất nhập khẩu tổng, khu vực trong nước/FDI (tháng, từ 2009, không theo mặt hàng/thị trường); FDI thực hiện và đăng ký (tháng, từ 2014); vốn đầu tư ngân sách nhà nước (tháng, từ 2010); IIP (từ 2016); PMI chỉ số chính (từ 2015, không có đơn hàng mới/xuất khẩu); khối lượng sản xuất công nghiệp (dừng 12/2023); lãi suất điều hành (các lần đổi) và liên ngân hàng (mới từ khoảng 07/2026); Mỹ: GDP, lãi suất Fed, CPI, thất nghiệp, cán cân thương mại, nợ/GDP.

**Còn thiếu, cần nguồn khác:** tỷ giá USD/VND, tín dụng và cung tiền, PMI đơn hàng, xuất khẩu theo mặt hàng và thị trường, dầu, vàng, lợi suất UST, chỉ số USD, Trung Quốc, EU, cước container, GPR/EPU (FRED, World Bank, IMF và các nguồn công bố); VN-Index và khối ngoại lấy từ `stock_db` của openstock.

## 6. Gu Tech Lead

Đã ghi vào `playbooks/tech-lead-taste.md` của workspace (nguồn `interview`, loại `declared`, `active`):

- **T-1** Logic dùng ở 2 chỗ thì tách ngay.
- **T-2** Sửa bug được dọn nhỏ trong chính hàm đang sửa nếu diff vẫn nhỏ.
- **T-3** Mọi nguồn dữ liệu đi qua adapter (phạm vi `macroeconomics`).
- **T-4** Nguồn lỗi thì giữ số cũ và báo rõ, không bao giờ điền số đoán (phạm vi `macroeconomics`).

**Chưa trả lời** (chưa ghi nguyên tắc nào): kiểu test và mức mock; điều kiện thêm dependency; khi nào chấp nhận giải pháp tạm; logic tính toán nằm ở tầng nào; câu hỏi đầu tiên khi nhận bug.

## 7. Câu hỏi còn mở

1. Thu thập dữ liệu Việt Nam ngoài dautubenvung: GSO/NHNN thường không có API chuẩn (website, PDF, Excel) → cần quyết định cách lấy và tần suất cập nhật; kiểm tra điều khoản sử dụng của từng nguồn.
2. PMI chi tiết (đơn hàng mới, đơn hàng xuất khẩu) có thể phải trả phí: dùng số chính công bố miễn phí hay mua dữ liệu.
3. Chạy ở đâu: máy cá nhân (Docker) hay VPS; lịch cập nhật dữ liệu.
4. Kết nối `stock_db` của openstock: chạy cùng máy, tài khoản chỉ đọc.
5. Phần gu Tech Lead (phỏng vấn 10–15 câu) để bootstrap `tech-lead-taste.md`.
