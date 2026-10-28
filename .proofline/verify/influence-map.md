## Proofline verify: influence-map

Base `main` @ `1e173a0` · nhánh @ `eea2a13` · 2 lượt mỗi bên · 2026-10-28T09:18:10+00:00

| Gate | Kết quả | Chi tiết |
| :--- | :--- | :--- |
| `commands_approved` | ✅ | lệnh kiểm tra đúng bản người đã duyệt (e11b6b9, 2026-10-28) |
| `acceptance_unchanged` | ✅ | journey đúng bản người đã duyệt (5e0a821, qua terminal, 2026-10-28) |
| `test_integrity` | ✅ | không sửa/xóa test cũ, không thêm skip |
| `new_tests_added` | ✅ | 1 file test mới: tests/test_influence.py |
| `acceptance_fails_before` | ✅ | 3/3 test của journey fail ở khẳng định trên base |
| `acceptance_passes_after` | ✅ | 3/3 test của journey pass |
| `no_regression` | ✅ | không test nào xấu đi so với base · base: 0, 0 fail · nhánh: 0, 0 fail (theo lượt) |
| `static_typecheck` | ✅ | 'uv run mypy && pnpm --dir web typecheck' sạch trên nhánh |
| `static_lint` | ✅ | 'uv run ruff check . && uv run ruff format --check .' sạch trên nhánh |

**Tổng: ✅ pass**
