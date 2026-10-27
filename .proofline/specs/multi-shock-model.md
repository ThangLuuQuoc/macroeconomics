# Spec (nháp): Mô hình nhiều cú sốc cùng lúc và cầu toàn cầu

> Tính năng thứ năm, **làm sau `backtest`**. Trạng thái: **nháp**, chưa có acceptance journey; journey viết khi bắt đầu, dựa trên thước đo của `backtest`.
> Liên quan: [`scenario-simulation.md`](scenario-simulation.md), [`backtest.md`](backtest.md), [`../data-sources.md`](../data-sources.md).

## 1. Vấn đề

Phép thử năm 2022 (2026-10-27) cho thấy ba điểm yếu của mô hình v1:
1. **Từng cú sốc riêng lẻ:** mỗi cú sốc được ước lượng một mình, nên khi các cú sốc xảy ra cùng lúc và liên quan nhau (dầu, lãi suất Mỹ, USD năm 2022), kết quả từng cú sốc mâu thuẫn nhau (CPI: +5,1; +4,8; −9,5) và không cộng được.
2. **Thiếu cầu toàn cầu:** tăng trưởng xuất khẩu giảm 40 điểm % năm 2022, mô hình chỉ giải thích khoảng 3 điểm; nguyên nhân chính là cầu của các thị trường mua hàng của Việt Nam, không có trong mô hình.
3. **Giai đoạn Covid và hiệu ứng nền:** tăng trưởng so cùng kỳ năm 2021–2022 bị méo do nền thấp năm 2020; mô hình coi đó là quan hệ bình thường.

## 2. Phạm vi dự kiến

1. **Một hồi quy cho mọi cú sốc** (local projections nhiều biến): mỗi biến kết quả, mỗi tầm h, hồi quy trên **cả ba cú sốc cùng lúc** cộng biến cầu toàn cầu; giả lập kịch bản cho phép đặt độ lớn từng cú sốc (để trống = 0). Tác động không còn bị đếm trùng.
2. **Cầu toàn cầu**, theo thứ tự ưu tiên nguồn (đều phải qua kiểm `verified` trong registry trước khi dùng):
   - Sản xuất công nghiệp Mỹ (FRED `INDPRO`), sản xuất công nghiệp Trung Quốc và EU (DBnomics: NBS, Eurostat);
   - hoặc nhập khẩu của Mỹ, Trung Quốc, EU từ Việt Nam (Comtrade, dữ liệu đối chiếu, `is_proxy: true`).
   Biến cầu toàn cầu vừa là **biến kiểm soát** vừa là **cú sốc thứ tư** có thể giả lập ("cầu thế giới giảm 5%").
3. **Covid:** biến giả cho 02/2020–12/2021 (khai báo rõ trên trang), và dùng **mức đã hiệu chỉnh mùa vụ, thay đổi so với tháng trước** thay cho tăng trưởng so cùng kỳ ở các biến dạng mức (xuất khẩu), để tránh hiệu ứng nền.
4. **Giữ v1 để so sánh:** trang kiểm chứng hiện **cả hai mô hình** cạnh nhau.

## 3. Tiêu chí nghiệm thu dự kiến (chốt khi viết journey)

- Trên trang kiểm chứng (dữ liệu thật): mô hình mới có tỷ lệ MAE so với "không đổi" **thấp hơn v1** với xuất khẩu và CPI; nếu không đạt thì **không thay v1** ở trang giả lập.
- Giả lập nhiều cú sốc cùng lúc: kết quả bằng tổng tuyến tính các phản ứng của **cùng một mô hình** (không còn mâu thuẫn như v1).
- Dữ liệu tổng hợp có quan hệ biết trước cho cả hai cú sốc tương quan nhau: mô hình mới tách đúng hệ số của từng cú sốc, v1 thì không.

## 4. Câu hỏi mở

1. Biến cầu toàn cầu nào trước: sản xuất công nghiệp của đối tác (đầy đủ, nhanh) hay nhập khẩu từ Việt Nam (sát hơn nhưng là dữ liệu đối chiếu, trễ hơn)?
2. Hiệu chỉnh mùa vụ: dùng X-13 (cần cài thêm chương trình) hay STL của `statsmodels`?
3. Có làm BVAR sau đó không, hay giữ local projections?
