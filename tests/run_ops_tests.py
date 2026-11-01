"""Runner kiểm thử độc lập cho bộ test ops contract (không phụ thuộc pytest)."""

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tests.test_ops_contract as ops_tests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    test_functions = [
        getattr(ops_tests, name)
        for name in dir(ops_tests)
        if name.startswith("test_") and callable(getattr(ops_tests, name))
    ]

    print("=" * 70)
    print(f"BẮT ĐẦU CHẠY {len(test_functions)} ACCEPTANCE CRITERIA TESTS (US-023..US-038)")
    print("=" * 70)

    passed = 0
    failed = 0

    for fn in test_functions:
        test_name = fn.__name__
        doc = (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else ""
        try:
            fn()
            print(f"  [PASS] {test_name}: {doc}")
            passed += 1
        except Exception:
            print(f"  [FAIL] {test_name}: {doc}")
            traceback.print_exc()
            failed += 1

    print("=" * 70)
    print(f"KẾT QUẢ: {passed} PASSED, {failed} FAILED / Tổng số {len(test_functions)} tests")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

