# US-015 / US-016: test evidence and runbook

## US-015: Data contract

The training CSVs have one header row, one sample row, 93 ordered float fields:
21 hand points (x,y,z) and 10 face points (x,y,z); face indices are
10,152,234,454,33,263,1,61,291,199. Coordinate z may be negative.

Run lightweight tests (no TF, model, camera or cloud credentials):

```bash
python -m pip install -r requirements-test.txt
python -m pytest tests/test_data_contract.py tests/test_notebook_parity.py -v
```

The tests examine *actual CSVs in this repository* for shape, header names,
order and finite numeric data. They also test rejection of malformed samples.

## US-016: Notebook/service parity

`test_notebook_parity.py` extracts the exact create_heatmap source from both
training and realtime notebooks and compares its uint8 pixels to the reusable
Python inference module on 23 real samples. This detects drift even if both
modules silently keep producing 224x224 images.

Run model-level parity on a machine with tensorflow and the real Git LFS model:

```bash
git lfs pull
# Windows PowerShell:
$env:TEST_KERAS_PARITY = '1'
python -m pytest tests/test_known_predictions.py -v
```

The optional test compares service output with notebook-style preprocessing
and the known 23/23 training-sample label sanity check documented in AGENTS.md.
These are *training* examples, not a real-world accuracy evaluation.

**Definition of Done:** light CI green + model-level parity run evidence
attached to PR. CI intentionally skips TF/model parity by default to keep PRs
fast. API service not yet guaranteed deployed just by passing these tests.
