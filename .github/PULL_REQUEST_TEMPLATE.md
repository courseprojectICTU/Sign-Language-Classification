# Pull Request: [Ticket/US-ID] - Mo ta ngan guc

## Muc dich
Mo ta ngan guc: PR nay giai quyet van de gi? Liet ke Issue/Story ID lien quan (VD: US-002, BUG-123).

---

## Loai thay doi
- [ ] Feature (tinh nang moi)
- [ ] Bugfix (sua loi)
- [ ] Refactor (tinh nang khong doi, chi sua cau truc code)
- [ ] Docs (cap nhat tai lieu)
- [ ] Chore (config, CI, script, dependency...)
- [ ] Hotfix (sua loi gap tren production)

---

## Thay doi chinh (Summary of Changes)

| Loai | File/Module | Mo ta thay doi |
|---|---|---|
| Feat/Refactor/... | `path/to/file` | Mo ta ngan guc thay doi |
| ... | ... | ... |

---

## Kiem tra Chat luong (Quality Gates)

| Tieu chi | Trang thai | Ghi chu |
|---|---|---|
| **Unit Test** | [ ] Pass / [ ] Khong co | Chay: `pytest tests -v` |
| **Regression Test** | [ ] Pass / [ ] Khong co | Chay: `pytest tests/test_pipeline_baseline.py -v` |
| **Build / Syntax** | [ ] Pass / [ ] Khong co | Python syntax OK, Notebook JSON valid |
| **Lint / Format** | [ ] Pass / [ ] Khong co | (Neu co linter) |
| **Backward Compatibility** | [ ] Dam bao / [ ] Co breaking change | Neu co breaking change -> Ghi chu trong PR description |

---

## Kiem thu (Test Evidence)

| Test Suite | Lenh chay | Ket qua (Pass/Fail) | Screen/Log |
|---|---|---|---|
| Unit Test | `pytest tests -v` | [ ] Pass / [ ] Fail | [DROP_SCREENSHOT] |
| Regression | `pytest tests/test_pipeline_baseline.py -v` | [ ] Pass / [ ] Fail | [DROP_SCREENSHOT] |
| Khac (neu co) | ... | [ ] Pass / [ ] Fail | [DROP_SCREENSHOT] |

> **Luu y:** Test phai chay tren `.venv\Scripts\python.exe` (hoac `D:\program\python\python.exe`).

---

## Anh minh chung (Screenshot/Artifacts)

> Reviewer kiem tra truc tiep tren GitHub/GitLab. Keo tha anh vao cac placeholder duoi.

| Loai | Anh minh chung |
|---|---|
| Test Suite (pytest) | ![Pytest Result](DROP_SCREENSHOT_PYTEST_HERE) |
| Regression Pipeline | ![Pipeline](DROP_SCREENSHOT_PIPELINE_HERE) |
| Khac (neu co) | ![Other](DROP_SCREENSHOT_OTHER_HERE) |

---

## Checklist Reviewer (Tick khi review)

- [ ] Code tuan thu coding convention / coding standard du an.
- [ ] Khong co dead code, commented code, `print` debug con sot lai.
- [ ] Bien/ham dat ten ro rang, tuan thu naming convention.
- [ ] Khong co hard-code gia tri magic number/string (truc tiep trong code).
- [ ] Docstring/Comment cho cac ham/public class moi.
- [ ] Khong co hard-code duong dan tuyet doi (duong dan Windows `D:\...`).
- [ ] Khong commit file rac (`__pycache__`, `.pytest_cache`, `.venv`, file lock `~$*`).
- [ ] Test moi (neu co) da duoc them vao `tests/` va pass.
- [ ] Cap nhat tai lieu (`docs/`, `README.md`, `CHANGELOG.md` neu co) neu co thay doi API/Behavior.
- [ ] Khong co breaking change khong duoc ghi chu / thong bao.

---

## Anh minh chung (Screenshot/Artifacts) - Bat buoc neu co thay doi UI/Behavior

| Loai | Anh minh chung |
|---|---|
| UI / Chuc nang moi | ![UI Screenshot](DROP_SCREENSHOT_UI_HERE) |
| Terminal / Log build/test | ![Terminal](DROP_SCREENSHOT_TERMINAL_HERE) |
| Khac | ![Other](DROP_SCREENSHOT_OTHER_HERE) |

---

## Checklist Tac gia (Self-review truoc khi gui PR)

- [ ] Da chay toan bo test suite (`pytest tests -v`) -> **10/10 passed**.
- [ ] Da chay regression pipeline (`pytest tests/test_pipeline_baseline.py -v`) -> **23/23 passed**.
- [ ] Da chay test lien quan den thay doi (neu co) -> Pass.
- [ ] Da xoa code debug, `print`, `console.log`, `debugger` neu co.
- [ ] Da cap nhat tai lieu (`docs/`, `README.md`, `CHANGELOG.md` neu co) neu co thay doi API/Behavior.
- [ ] Da kiem tra `git diff` -> khong co file rac, khong co file lon (>10MB) khong can thiet.
- [ ] Da kiem tra `.gitignore` da chua cac pattern can thiet (`.venv/`, `__pycache__/`, `.pytest_cache/`, `~$*`, `*.npz` neu can).

---

## Ghi chu / Mo ta them (Optional)

Mo ta them neu co (breaking change, migration steps, performance impact, security note, rollback plan...).

---

## Lien quan
- **Issue/Story ID:** [US-XXX / BUG-XXX]
- **Epic:** [EPC-XXX]
- **Branch:** `[feature|bugfix|hotfix|docs|chore]/[ID]`
- **Base branch:** `develop`
- **Deploy target:** [Staging / Production / None]

---

> **Luu y cho Reviewer:** Neu PR nay co chua breaking change, vui long ghi ro rang trong phan "Ghi chu / Mo ta them" va danh dau `Breaking Change` trong Checklist.