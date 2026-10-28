# Spec (nháp): Dữ liệu giả lập có đáp án biết trước

> Tính năng thứ sáu, **làm trước `influence-map`**. Trạng thái: **nháp, đã chốt câu hỏi mở** (2026-10-28), chưa có acceptance journey.
> Liên quan: [`scenario-simulation.md`](scenario-simulation.md), [`backtest.md`](backtest.md), [`influence-map.md`](influence-map.md); gate chỉ số nghiệp vụ của Proofline (docs/09 của Proofline, mục 3).

## 1. Vấn đề

1. **Không biết mô hình có đúng không.** Trên số thật không ai biết hệ số thật là bao nhiêu, nên khi mô hình cho "dầu tăng 20% thì CPI +5 điểm" thì không kiểm được đó là đúng hay là lỗi code. Backtest trên số thật cho biết mô hình **đoán** tốt tới đâu, nhưng mỗi lần lấy dữ liệu mới thì số đổi, nên không dùng làm thước đo ổn định cho gate được.
2. **Khó dựng tình huống để xem và thử giao diện.** Muốn xem trang khi có cú sốc lớn, khi thiếu một chuỗi, khi nguồn lỗi, hoặc với những yếu tố chưa có nguồn thật, hiện phải đợi chuyện đó xảy ra thật hoặc tự viết tay bản ghi nguồn trong test (`tests/journeys/support.py`).
3. **Màn hình mới (`influence-map`) cần dữ liệu cho ra cùng kết quả mỗi lần chạy** để journey kiểm được màu, kích thước, hướng.

## 2. Phạm vi

### 2.1. Kịch bản giả lập

Một tệp YAML trong `backend/macro/synthetic/scenarios/<tên>.yaml`:

```yaml
name: baseline
seed: 42
start: 2005-01
end: 2036-12
series:                      # quá trình sinh, khai báo trong KHÔNG GIAN MÔ HÌNH DÙNG (x_t, y_t)
  global.brent:   {process: ar1, mean: 0, phi: 0.2, sd: 6}       # x_t = thay đổi log %, như SHOCKS
  us.ust10y:      {process: ar1, mean: 0, phi: 0.1, sd: 0.2}
  us.usd_broad:   {process: ar1, mean: 0, phi: 0.3, sd: 1.5}
  vn.pmi_mfg:     {process: random_walk, start: 50, sd: 0.3}
  vn.iip:         {process: noise, mean: 8, sd: 2}
  vn.vnindex:     {process: random_walk, start: 709, sd: 4}       # y_t = 100·log(điểm), ~1200 điểm
  vn.gdp_yoy:                                                      # xem 2.2
    process: bounded
    before: {mean: 6.5, phi: 0.8, sd: 0.4}
    from: 2026-01
    lower: 9
    upper: 15
cpi: {overlap_months: 24, offset: 0}   # hai chuỗi thành phần của CPI, xem mục 3 dưới đây
relations:                   # quan hệ gài vào: y_t += beta · x_{t-lag}
  - {outcome: vn.pmi_mfg, shock: global.brent, beta: 0.2, lag: 1}
  - {outcome: vn.vnindex, shock: global.brent, beta: -0.3, lag: 1}
  - {outcome: vn.gdp_yoy, shock: global.demand, beta: 0.15, lag: 2}
events:                      # cú sốc gài vào một tháng cụ thể (cộng thêm vào quá trình)
  - {series: global.brent, period: 2022-03, add: 25}
missing: []                  # chuỗi cố ý không có
```

1. **Sinh số:** `ar1`, `random_walk`, `noise`, `bounded`; quan hệ tuyến tính có trễ; sự kiện cộng thêm một tháng. Cùng tệp và cùng `seed` thì ra **đúng từng con số như nhau**.
2. **Đổi về đơn vị nguồn:** quá trình được khai báo theo đúng biến mà mô hình dùng (sau phép biến đổi trong `scenario.py`), rồi bộ sinh **đổi ngược** về chuỗi gốc theo `series_id` và đơn vị của nguồn thật: thay đổi log → mức giá; chênh lệch → mức lợi suất; tăng trưởng so cùng kỳ của xuất khẩu → mức xuất khẩu (12 tháng đầu là mức nền); `100·log` của VN-Index → điểm chỉ số. Nhờ vậy mọi trang hiện có chạy trên dữ liệu giả **không cần sửa gì**.
3. **CPI sinh cả hai chuỗi thành phần** (`vn.cpi_yoy_imf` và `vn.cpi_yoy`), chồng nhau `cpi.overlap_months` tháng, trên đoạn chồng thì `vn.cpi_yoy = vn.cpi_yoy_imf + cpi.offset`, để phần nối chuỗi của trang giả lập cũng được thử (`offset` vượt `SPLICE_TOLERANCE` thì nối thất bại).
4. **Kế thừa:** `extends: <tên>` lấy toàn bộ một kịch bản khác rồi ghi đè các khoá khai báo thêm.

### 2.2. GDP theo tháng và các yếu tố chỉ có trong giả lập

Dữ liệu giả lập có thêm những chuỗi **chưa có nguồn thật**, để màn hình bong bóng đủ thành phần:

| `series_id` | Tên | Vai trò | Biến đổi mô hình dùng |
|---|---|---|---|
| `vn.gdp_yoy` | GDP (so cùng kỳ, theo tháng) | biến kết quả | giữ nguyên |
| `global.demand` | Cầu thế giới (sản xuất công nghiệp đối tác, so cùng kỳ) | yếu tố, ngoài nước | chênh lệch |
| `vn.policy_rate` | Lãi suất điều hành NHNN | yếu tố, trong nước | chênh lệch |
| `vn.usdvnd` | Tỷ giá USD/VND | yếu tố, trong nước | thay đổi log % |
| `vn.fdi_disbursed` | FDI giải ngân (so cùng kỳ) | yếu tố, trong nước | chênh lệch |
| `vn.credit_growth` | Tăng trưởng tín dụng (so cùng kỳ) | yếu tố, trong nước | chênh lệch |
| `vn.public_investment` | Giải ngân đầu tư công (so cùng kỳ) | yếu tố, trong nước | chênh lệch |

- **GDP (`process: bounded`)**: trước `from` là AR(1) quanh 6,5%; từ **01/2026 tới 12/2036**, tăng trưởng so cùng kỳ **luôn trong khoảng 9%–15%**: `g_t = 9 + 6·sigmoid(z_t)`, với `z_t` là AR(1) cộng các quan hệ gài vào. Các yếu tố vẫn tác động lên GDP nhưng qua hàm chặn, nên tác động **không tuyến tính**; GDP vì vậy **không** nằm trong chỉ số `recovery_error` (2.4), `truth.json` đánh dấu các quan hệ này `bounded: true`. Bước nhảy từ ~6,5% lên ≥ 9% ở 01/2026 là chủ ý, trang hiện nó như mọi chuỗi khác.
- **Danh mục yếu tố** (`SHOCKS` trong `scenario.py`) được mở rộng bằng các chuỗi trên, mỗi yếu tố có `scope: global | domestic`. Trang giả lập, trang kiểm chứng và bản đồ ảnh hưởng **chỉ dùng yếu tố có dữ liệu** trong database đang xem; ở chế độ số thật, các yếu tố chưa có nguồn được liệt kê một dòng "Chưa có dữ liệu thật: …".
- `vn.gdp_yoy` được thêm vào danh mục biến kết quả (`OUTCOMES`); ở chế độ số thật nó báo "chưa đủ dữ liệu" như các biến thiếu khác.
- Yếu tố trong nước (lãi suất, tín dụng…) **phụ thuộc lẫn nhau** với nền kinh tế; trong giả lập điều đó không quan trọng vì quan hệ do mình gài, nhưng khi có số thật thì phải xét lại (ghi ở trang khi chạy số thật).

### 2.3. Bật giả lập ngay trong app đang chạy

1. **Database riêng `macro_synthetic`** trên cùng máy chủ Postgres với database thật (lấy từ `MACRO_DATABASE_URL`, chỉ đổi tên database; ghi đè được bằng `MACRO_SYNTHETIC_DATABASE_URL`). App **tự tạo** database này lần đầu cần tới; không tạo được (thiếu quyền) thì báo rõ lỗi và cách sửa, chế độ số thật vẫn chạy.
2. **Công tắc trên đầu mọi trang:** "Dữ liệu: **Thật** | **Giả lập**". Chọn Giả lập thì hiện danh sách kịch bản có sẵn và ô seed (mặc định seed của kịch bản). Chọn kịch bản: app **nạp lại** `macro_synthetic` (xoá dữ liệu giả cũ, sinh mới), trong lúc nạp hiện trạng thái đang nạp; xong thì trang hiện tại tải lại trên dữ liệu giả.
3. **Chế độ theo từng trình duyệt** (cookie `macro_data=real|synthetic`): người khác đang xem số thật không bị đổi. Kịch bản đang nạp trong `macro_synthetic` là chung cho cả app (chỉ có một database giả lập).
4. Mọi API đọc số liệu (`/api/indicators`, `/api/scenario`, `/api/backtest`, `/api/influence`…) đọc từ database theo chế độ của yêu cầu; không có cookie thì là số thật.
5. CLI vẫn có để dùng trong test và tự động hoá: `python -m macro.ingest --synthetic <tên|tệp> [--seed N]` (mặc định ghi vào `macro_synthetic`).

### 2.4. Không trộn với số thật

- Bộ sinh **chỉ** ghi vào database giả lập; `fetch_runs.connector = 'synthetic'`, `raw_path` ghi tên kịch bản và seed.
- `ingest --synthetic` **từ chối** (không ghi gì, thoát mã ≠ 0, thông báo bắt đầu bằng `Từ chối:`) nếu database đích đã có lần lấy thật; `ingest` thường **từ chối** theo cùng cách nếu database đã có lần lấy giả lập.
- `python -m macro.measure` (gate chỉ số trên số thật) luôn đọc database thật, kể cả khi có cookie hay biến môi trường giả lập.
- `GET /api/data-mode` trả `{"mode": "synthetic", "scenario": "baseline", "seed": 42, "scenarios": [...]}` hoặc `{"mode": "real", "scenarios": [...]}`.
- Khi đang xem giả lập, **mọi trang** hiện dải cố định trên cùng: "DỮ LIỆU GIẢ LẬP — kịch bản baseline, seed 42. Không phải số liệu thật."; nhãn nguồn của từng chỉ số là "Giả lập (baseline)".

### 2.5. Kịch bản có sẵn

- `baseline`: đủ mọi chuỗi ở 2.1 và 2.2, từ 01/2005 tới 12/2036, đủ dài cho backtest (≥ 60 quan sát ở mọi tầm); là kịch bản mặc định khi bật giả lập.
- `shock-2022`: như `baseline` cộng một cú sốc dầu, lãi suất và USD cùng lúc năm 2022 (để thử giả lập nhiều cú sốc sau này).
- `missing-data`: thiếu CPI và USD.
- `source-failure`: lần lấy thứ hai ghi lỗi; kiểm quy tắc T-4 (giữ số cũ, báo rõ).
- `cpi-mismatch`: như `baseline` nhưng `cpi.offset: 0.5`, để thử trường hợp nối CPI thất bại.
- `influence-demo`: do spec `influence-map` khai báo.

### 2.6. Đo khả năng tìm lại đáp án

`python -m macro.synthetic recover --scenario baseline --out FILE`: nạp kịch bản vào một database tạm (không đụng `macro_synthetic` đang xem), chạy **đúng hàm ước lượng của trang giả lập**, so với `truth.json`, ghi JSON:

```json
{
  "data_snapshot": "synthetic:baseline:42",
  "relations": {
    "vn.pmi_mfg<-global.brent": {"truth": 0.2, "horizons": [{"h": 1, "estimate": 0.19, "lower": 0.12, "upper": 0.26, "covered": true}], "max_rel_error": 0.08, "coverage": 1.0}
  },
  "mean_rel_error": 0.08,
  "max_rel_error": 0.15,
  "null_pairs": {"vn.iip<-global.brent": {"false_positive_share": 0.0}},
  "false_positive_share": 0.0
}
```

- `mean_rel_error` (chỉ số của gate) và `max_rel_error`: trung bình và lớn nhất của `|ước lượng − thật| / |thật|` trên mọi quan hệ gài **tuyến tính** (bỏ quan hệ `bounded`) và mọi tầm h = 1..12. Gate dùng **trung bình**: sai số mẫu ở tầm dài có độ lệch chuẩn ~16% (mẫu 2005–2036), nên giá trị lớn nhất của 24 con số nhiễu không ổn định (đo trên 60 seed: `max ≤ 0,25` chỉ đạt 70%, `mean ≤ 0,2` đạt 97%). Đáp án thật ở tầm h là phản ứng cộng dồn theo quá trình đã khai báo (vd bước ngẫu nhiên với một trễ: bằng `beta` ở mọi h ≥ 1).
- `false_positive_share`: với các cặp **không** gài quan hệ, tỷ lệ tầm h mà khoảng tin cậy 90% **không** chứa 0.
- `--truth FILE` (JSON `{"relations": [...]}`, cùng dạng `relations` của kịch bản) thay đáp án lấy từ kịch bản; chỉ để kiểm rằng phép đo bắt được đáp án sai.

**Gate chỉ số** khai báo trong manifest của spec này (`kind: fixture`, chặn). Ngưỡng **tạm thời** (2026-10-28, sửa cùng ngày sau khi đo nhiễu thật), xem lại sau khi đã chạy và xem kết quả trên giao diện:

```yaml
metrics:
  - name: recovery_error
    command: uv run python -m macro.synthetic recover --scenario baseline --out {out}
    value: .mean_rel_error
    threshold: {max: 0.2}
    files: [backend/macro/synthetic/recover.py, backend/macro/synthetic/generate.py, backend/macro/synthetic/scenarios/baseline.yaml]
  - name: false_positive
    command: uv run python -m macro.synthetic recover --scenario baseline --out {out}
    value: .false_positive_share
    threshold: {max: 0.2}
    files: [backend/macro/synthetic/recover.py, backend/macro/synthetic/generate.py, backend/macro/synthetic/scenarios/baseline.yaml]
```

Từ đó về sau, mọi thay đổi mô hình (vd `multi-shock-model`) phải giữ được hai chỉ số này, nếu không gate báo fail.

**Khi nào khai báo `metrics` vào manifest:** `recover.py` và `baseline.yaml` chưa có lúc duyệt spec này, nên Proofline sẽ khoá chúng ở trạng thái "absent" và báo `metrics_unchanged` fail ngay khi viết ra. Vì vậy: lần duyệt đầu **chưa** có `metrics`; ngưỡng của tính năng này được giữ bằng chính journey (mục 3, ý 11, gọi `recover` và so ngưỡng). Khi code xong và journey đạt, thêm khối `metrics` ở trên vào manifest và chủ dự án duyệt lại trong terminal, trước khi merge; từ đó gate chỉ số bảo vệ các thay đổi sau.

**Không làm:** giao diện để soạn hay sửa kịch bản (chỉ chọn trong danh sách có sẵn và đổi seed); nhiều database giả lập cùng lúc; sinh dữ liệu theo mùa vụ hay phân phối đuôi dày; giả lập định dạng bản gốc của từng nguồn thật (đã có trong test journey, giữ nguyên).

## 3. Tiêu chí nghiệm thu dự kiến (chốt khi viết journey)

Kiểm bằng `tests/journeys/test_synthetic_data.py`:

1. App đang chạy trên số thật (một bộ số nạp sẵn). Bật **Giả lập**, chọn `baseline`: `macro_synthetic` được tự tạo và nạp; trang tổng quan, trang giả lập và trang kiểm chứng đều có dải "DỮ LIỆU GIẢ LẬP" và nhãn nguồn "Giả lập (baseline)".
2. Chuyển về **Thật**: không còn dải giả lập, mọi số trên trang tổng quan **giống hệt** trước khi bật giả lập; database thật không có lần lấy `synthetic` nào.
3. Hai trình duyệt: một bên bật giả lập, bên kia vẫn thấy số thật.
4. Nạp `baseline` hai lần: số giống hệt nhau; đổi seed: số khác.
5. `ingest --synthetic` vào database đã có lần lấy thật: báo lỗi, không ghi gì; `ingest` thường vào database giả lập: báo lỗi, không ghi gì.
6. Trang giả lập trên `baseline`, cú sốc dầu: PMI có khoảng tin cậy không chứa 0 và ước lượng trong ±40% của `0,2` ở mọi tầm; IIP (không gài quan hệ) có khoảng tin cậy chứa 0. Danh sách cú sốc có cả các yếu tố ở 2.2.
7. GDP trên `baseline`: mọi tháng từ 01/2026 tới 12/2036 có tăng trưởng trong [9%, 15%].
8. CPI trên `baseline`: trang giả lập có phản ứng của CPI (nối từ hai chuỗi thành phần); `cpi-mismatch`: báo "Chưa nối được lịch sử CPI" như với số thật.
9. `missing-data`: trang kiểm chứng báo CPI "Chưa đủ dữ liệu để kiểm chứng" và liệt kê USD là cú sốc thiếu. `source-failure`: trang tổng quan giữ số của lần lấy trước và báo "Nguồn lỗi".
10. Ở chế độ số thật, các yếu tố ở 2.2 không có trong danh sách cú sốc, và có dòng "Chưa có dữ liệu thật: …".
11. `recover` trên `baseline`: `mean_rel_error ≤ 0,2`, `false_positive_share ≤ 0,2`; đáp án sai (`--truth` gấp đôi mọi β) thì `mean_rel_error` vượt ngưỡng — để chắc phép đo không luôn đạt.

## 4. Hợp đồng giao diện

- `data-testid=data-mode-switch` trên mọi trang, với `data-testid=mode-real`, `data-testid=mode-synthetic`, `data-testid=scenario-select`, `data-testid=seed-input`, nút `data-testid=load-synthetic`, `data-testid=synthetic-loading` khi đang nạp.
- `data-testid=synthetic-banner` trên mọi trang khi đang xem giả lập, có thuộc tính `data-scenario`, `data-seed`; không có phần tử này khi xem số thật.
- `data-testid=no-real-data` liệt kê các yếu tố chưa có dữ liệu thật.
- API: `GET /api/data-mode`; `POST /api/synthetic/load` với `{"scenario": "baseline", "seed": 42}` (nạp lại `macro_synthetic`, trả khi xong); chế độ theo cookie `macro_data`.
- CLI: `python -m macro.ingest --synthetic <tên|tệp> [--seed N] [--database-url URL]`; `python -m macro.synthetic recover --scenario <tên|tệp> [--truth FILE] --out FILE`.
- Cấu hình: `Settings.synthetic_database_url` (mặc định: `database_url` đổi tên database thành `macro_synthetic`; biến môi trường `MACRO_SYNTHETIC_DATABASE_URL`).

## 5. Quyết định của chủ dự án

- 2026-10-28: làm dữ liệu giả lập trước màn hình bong bóng (`influence-map`); dữ liệu giả không được trộn với số thật và luôn phải nhìn thấy được trên giao diện.
- 2026-10-28, câu hỏi mở:
  1. Ngưỡng `recovery_error ≤ 0,25` và `false_positive ≤ 0,2`: chấp nhận **tạm thời**, xem lại sau khi xem kết quả trên giao diện.
- 2026-10-28, sau khi làm: tiêu chí ban đầu quá chặt so với sai số mẫu thật (đo trên 60 seed: khoảng tin cậy của PMI chứa 0,2 ở cả 12 tầm chỉ đạt 57%, sai lệch lớn nhất ≤ 0,25 đạt 70%; seed 42 cho 0,30). Chủ dự án quyết định: `recovery_error` dùng **sai lệch trung bình ≤ 0,2**; PMI kiểm **khoảng tin cậy không chứa 0 và ước lượng trong ±40% của 0,2** ở mọi tầm; không đổi seed để test đạt.
  2. Database giả lập có tên riêng `macro_synthetic`, app tự tạo và tự nối tới khi người dùng chọn xem giả lập.
  3. Giả lập là một tính năng **ngay trong app đang chạy** (công tắc Thật/Giả lập), không phải một lệnh chạy app riêng.
  4. Kịch bản sinh **cả hai** chuỗi thành phần của CPI.
- 2026-10-28, từ câu trả lời cho `influence-map`: giả lập GDP theo tháng, từ 2026 tới 10 năm sau tăng trưởng luôn trong 9%–15%; thêm đủ các yếu tố (cầu thế giới, lãi suất điều hành, tỷ giá, FDI, tín dụng, đầu tư công) vì đang là dữ liệu giả lập.
