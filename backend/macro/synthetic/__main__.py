"""`python -m macro.synthetic recover …` (spec synthetic-data mục 2.6)."""

from __future__ import annotations

import sys

from macro.synthetic import recover

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "recover":
        print(
            "Cách dùng: python -m macro.synthetic recover --scenario TÊN --out FILE",
            file=sys.stderr,
        )
        raise SystemExit(2)
    raise SystemExit(recover.main(sys.argv[2:]))
