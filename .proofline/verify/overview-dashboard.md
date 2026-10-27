## Proofline verify: overview-dashboard

Base `main` @ `95e2487` · nhánh @ `595b345` · 2 lượt mỗi bên · 2026-10-27T03:19:44+00:00

| Gate | Kết quả | Chi tiết |
| :--- | :--- | :--- |
| `acceptance_unchanged` | ✅ | journey đúng bản đã duyệt (9ecfd34) |
| `test_integrity` | ✅ | không sửa/xóa test cũ, không thêm skip |
| `new_tests_added` | ✅ | 1 file test mới: tests/test_overview.py |
| `acceptance_fails_before` | ✅ | 3/3 test của journey fail ở khẳng định trên base |
| `acceptance_passes_after` | ✅ | 3/3 test của journey pass |
| `no_regression` | ✅ | không test nào xấu đi so với base · base: 0, 0 fail · nhánh: 0, 0 fail (theo lượt) |
| `static_typecheck` | ✅ | 'uv run mypy && pnpm --dir web typecheck' sạch trên nhánh |
| `static_lint` | ✅ | 'uv run ruff check . && uv run ruff format --check .' sạch trên nhánh |

**Tổng: ✅ pass**
