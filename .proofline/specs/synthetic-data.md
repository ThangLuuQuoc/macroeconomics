# Spec (nháp): Dữ liệu giả lập có đáp án biết trước

> Tính năng thứ sáu, **làm trước `influence-map`**. Trạng thái: **nháp**, chưa có acceptance journey; journey viết sau khi chốt các câu hỏi ở mục 6.
> Liên quan: [`scenario-simulation.md`](scenario-simulation.md), [`backtest.md`](backtest.md), [`influence-map.md`](influence-map.md); gate chỉ số nghiệp vụ của Proofline (docs/09 của Proofline, mục 3).

## 1. Vấn đề

1. **Không biết mô hình có đúng không.** Trên số thật không ai biết hệ số thật là bao nhiêu, nên khi mô hình cho "dầu tăng 20% thì CPI +5 điểm" thì không kiểm được đó là đúng hay là lỗi code. Backtest trên số thật cho biết mô hình **đoán** tốt tới đâu, nhưng mỗi lần lấy dữ liệu mới thì số đổi, nên không dùng làm thước đo ổn định cho gate được.
2. **Khó dựng tình huống để thử giao diện.** Muốn xem trang khi có cú sốc lớn, khi thiếu một chuỗi, khi nguồn lỗi, hiện phải đợi chuyện đó xảy ra thật hoặc tự viết tay bản ghi nguồn trong test (`tests/journeys/support.py`).
3. **Màn hình mới (`influence-map`) cần dữ liệu cho ra cùng kết quả mỗi lần chạy** để journey kiểm được màu, kích thước, hướng.

## 2. Phạm vi

**Kịch bản giả lập** là một tệp YAML trong `backend/macro/synthetic/scenarios/<tên>.yaml`:

```yaml
name: baseline
seed: 42
start: 2005-01
end: 2026-09
series:                      # quá trình sinh, khai báo trong KHÔNG GIAN MÔ HÌNH DÙNG (x_t, y_t)
  global.brent:   {process: ar1, mean: 0, phi: 0.2, sd: 6}       # x_t = thay đổi log %, như SHOCKS
  us.ust10y:      {process: ar1, mean: 0, phi: 0.1, sd: 0.2}
  us.usd_broad:   {process: ar1, mean: 0, phi: 0.3, sd: 1.5}
  vn.pmi_mfg:     {process: random_walk, start: 50, sd: 0.3}
  vn.iip:         {process: noise, mean: 8, sd: 2}
  vn.vnindex:     {process: random_walk, start: 709, sd: 4}       # y_t = 100·log(điểm), ~1200 điểm
relations:                   # quan hệ gài vào: y_t += beta · x_{t-lag}
  - {outcome: vn.pmi_mfg, shock: global.brent, beta: 0.2, lag: 1}
  - {outcome: vn.vnindex, shock: global.brent, beta: -0.3, lag: 1}
events:                      # cú sốc gài vào một tháng cụ thể (cộng thêm vào quá trình)
  - {series: global.brent, period: 2022-03, add: 25}
missing: [vn.cpi_yoy, vn.cpi_yoy_imf]   # chuỗi cố ý không có
```

1. **Sinh số:** `ar1`, `random_walk`, `noise`; quan hệ tuyến tính có trễ; sự kiện cộng thêm một tháng. Cùng tệp và cùng `seed` thì ra **đúng từng con số như nhau**.
2. **Đổi về đơn vị nguồn:** quá trình được khai báo theo đúng biến mà mô hình dùng (sau phép biến đổi trong `scenario.py`), rồi bộ sinh **đổi ngược** về chuỗi gốc theo `series_id` và đơn vị của nguồn thật: thay đổi log → mức giá; chênh lệch → mức lợi suất; tăng trưởng so cùng kỳ của xuất khẩu → mức xuất khẩu (12 tháng đầu là mức nền); `100·log` của VN-Index → điểm chỉ số. Nhờ vậy mọi trang hiện có chạy trên dữ liệu giả **không cần sửa gì**.
3. **Connector `synthetic`:** theo interface `Connector`; `fetch` sinh số từ kịch bản (không gọi mạng) và ghi bản gốc kèm `truth.json` (các quan hệ đã gài); `parse` đọc lại. **Không** nằm trong `CONNECTORS`, chỉ chạy bằng `python -m macro.ingest --synthetic <tên hoặc đường dẫn tệp>`.
4. **Không trộn với số thật:**
   - `fetch_runs.connector = 'synthetic'`, `raw_path` ghi tên kịch bản và seed.
   - `ingest --synthetic` **từ chối** (không ghi gì, thoát mã ≠ 0) nếu database đã có lần lấy thật; `ingest` thường **từ chối** nếu database đã có lần lấy giả lập. Cách dùng: một database riêng, vd `macro_synthetic`.
   - `GET /api/data-mode` trả `{"mode": "synthetic", "scenario": "baseline", "seed": 42}` hoặc `{"mode": "real"}`.
   - Khi `mode = synthetic`, **mọi trang** hiện dải cố định trên cùng: "DỮ LIỆU GIẢ LẬP — kịch bản baseline, seed 42. Không phải số liệu thật."; nhãn nguồn của từng chỉ số là "Giả lập (baseline)".
5. **Kịch bản có sẵn:**
   - `baseline`: các quan hệ gài như ví dụ trên, đủ dài cho backtest (≥ 60 quan sát ở mọi tầm).
   - `shock-2022`: như `baseline` cộng một cú sốc dầu, lãi suất và USD cùng lúc năm 2022 (để thử giả lập nhiều cú sốc sau này).
   - `missing-data`: thiếu CPI và USD.
   - `source-failure`: lần lấy thứ hai ghi lỗi; kiểm quy tắc T-4 (giữ số cũ, báo rõ).
6. **Đo khả năng tìm lại đáp án** — `python -m macro.synthetic recover --scenario baseline --out FILE`: nạp kịch bản vào một database tạm, chạy **đúng hàm ước lượng của trang giả lập**, so với `truth.json`, ghi JSON:

   ```json
   {
     "data_snapshot": "synthetic:baseline:42",
     "relations": {
       "vn.pmi_mfg<-global.brent": {"truth": 0.2, "horizons": [{"h": 1, "estimate": 0.19, "lower": 0.12, "upper": 0.26, "covered": true}], "max_rel_error": 0.08, "coverage": 1.0}
     },
     "max_rel_error": 0.08,
     "null_pairs": {"vn.iip<-global.brent": {"false_positive_share": 0.0}},
     "false_positive_share": 0.0
   }
   ```

   - `max_rel_error`: lớn nhất của `|ước lượng − thật| / |thật|` trên mọi quan hệ gài và mọi tầm h = 1..12. Đáp án thật ở tầm h là phản ứng cộng dồn theo quá trình đã khai báo (vd bước ngẫu nhiên với một trễ: bằng `beta` ở mọi h ≥ 1).
   - `false_positive_share`: với các cặp **không** gài quan hệ, tỷ lệ tầm h mà khoảng tin cậy 90% **không** chứa 0.

**Gate chỉ số** khai báo trong manifest của spec này (`kind: fixture`, chặn):

```yaml
metrics:
  - name: recovery_error
    command: uv run python -m macro.synthetic recover --scenario baseline --out {out}
    value: .max_rel_error
    threshold: {max: 0.25}
    files: [backend/macro/synthetic/recover.py, backend/macro/synthetic/scenarios/baseline.yaml]
  - name: false_positive
    command: uv run python -m macro.synthetic recover --scenario baseline --out {out}
    value: .false_positive_share
    threshold: {max: 0.2}
    files: [backend/macro/synthetic/recover.py, backend/macro/synthetic/scenarios/baseline.yaml]
```

Từ đó về sau, mọi thay đổi mô hình (vd `multi-shock-model`) phải giữ được hai chỉ số này, nếu không gate báo fail.

**Không làm:** giao diện để soạn kịch bản; sinh dữ liệu theo đúng mùa vụ hay phân phối đuôi dày; giả lập định dạng bản gốc của từng nguồn thật (đã có trong test journey, giữ nguyên); quan hệ phi tuyến.

## 3. Tiêu chí nghiệm thu dự kiến (chốt khi viết journey)

Kiểm bằng `tests/journeys/test_synthetic_data.py`:

1. Nạp `baseline` vào database trống rồi mở app: trang tổng quan, trang giả lập và trang kiểm chứng đều có dải "DỮ LIỆU GIẢ LẬP" và nhãn nguồn "Giả lập (baseline)".
2. Nạp `baseline` hai lần vào hai database: số giống hệt nhau; đổi seed: số khác.
3. `ingest --synthetic` vào database đã có lần lấy thật: báo lỗi, không ghi gì; `ingest` thường vào database giả lập: báo lỗi, không ghi gì.
4. Trang giả lập trên `baseline`, cú sốc dầu: PMI có khoảng tin cậy chứa `0,2` ở mọi tầm và không chứa 0; IIP (không gài quan hệ) có khoảng tin cậy chứa 0.
5. `missing-data`: thẻ CPI và cú sốc USD báo "chưa đủ dữ liệu" như với số thật.
6. `source-failure`: trang tổng quan giữ số của lần lấy trước và báo lần lấy sau lỗi.
7. `recover` trên `baseline`: `max_rel_error ≤ 0,25`, `false_positive_share ≤ 0,2`; trong test có một kịch bản gài sai đáp án (`truth.json` lệch) thì `max_rel_error` vượt ngưỡng — để chắc phép đo không luôn đạt.

## 4. Hợp đồng giao diện

- `data-testid=synthetic-banner` trên mọi trang khi `mode = synthetic`, có thuộc tính `data-scenario`, `data-seed`; không có phần tử này khi `mode = real`.
- API: `GET /api/data-mode`.
- CLI: `python -m macro.ingest --synthetic <tên|tệp> [--seed N] --database-url URL`; `python -m macro.synthetic recover --scenario <tên|tệp> --out FILE`.

## 5. Quyết định của chủ dự án

- 2026-10-28: làm dữ liệu giả lập trước màn hình bong bóng (`influence-map`); dữ liệu giả không được trộn với số thật và luôn phải nhìn thấy được trên giao diện.

## 6. Câu hỏi mở

1. Ngưỡng `recovery_error ≤ 0,25` (sai lệch tương đối 25%) và `false_positive ≤ 0,2` có hợp lý không? Mẫu ~250 tháng với nhiễu như `baseline` thì sai lệch thường dưới 10%; ngưỡng chặt hơn thì dễ fail vì nhiễu, lỏng hơn thì bỏ sót lỗi.
2. Database giả lập: bắt buộc tên riêng (`macro_synthetic`) do app tự tạo, hay để người dùng truyền `--database-url` (app chỉ kiểm không trộn)?
3. Có cần chạy app ở chế độ giả lập bằng một lệnh (`python -m macro.serve --synthetic baseline`, tự nạp vào database tạm) để demo nhanh không?
4. CPI dùng chuỗi nối IMF + dautubenvung: kịch bản sinh cả hai chuỗi thành phần (để thử luôn phần nối) hay chỉ sinh chuỗi IMF?
