## Proofline verify: synthetic-data

Base `main` @ `134c59f` · nhánh @ `6b21a69` · 2 lượt mỗi bên · 2026-10-28T08:43:19+00:00

| Gate | Kết quả | Chi tiết |
| :--- | :--- | :--- |
| `commands_approved` | ✅ | lệnh kiểm tra đúng bản người đã duyệt (e11b6b9, 2026-10-28) |
| `acceptance_unchanged` | ✅ | journey đúng bản người đã duyệt (176cf1f, qua terminal, 2026-10-28) |
| `metrics_unchanged` | ✅ | chỉ số đúng bản đã duyệt (recovery_error, false_positive) |
| `test_integrity` | ✅ | không sửa/xóa test cũ, không thêm skip |
| `new_tests_added` | ✅ | 1 file test mới: tests/test_synthetic.py |
| `acceptance_fails_before` | ✅ | 7/7 test của journey fail ở khẳng định trên base |
| `acceptance_passes_after` | ✅ | 7/7 test của journey pass |
| `no_regression` | ✅ | không test nào xấu đi so với base · base: 0, 0 fail · nhánh: 0, 0 fail (theo lượt) |
| `metric_recovery_error` | ✅ | nhánh 0.1417 (ngưỡng ≤ 0.2), base không đo được (lệnh đo lỗi (exit 1): ve` to target the active environment instead
F:\2027\proof) |
| `metric_false_positive` | ✅ | nhánh 0.0817 (ngưỡng ≤ 0.2), base không đo được (lệnh đo lỗi (exit 1): ve` to target the active environment instead
F:\2027\proof) |
| `static_typecheck` | ✅ | 'uv run mypy && pnpm --dir web typecheck' sạch trên nhánh |
| `static_lint` | ✅ | 'uv run ruff check . && uv run ruff format --check .' sạch trên nhánh |

**Tổng: ✅ pass**
