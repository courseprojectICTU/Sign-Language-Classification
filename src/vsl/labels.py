"""Nguon chan ly duy nhat cho danh sach nhan va so lop (BR-003).

Quy tac:
- 23 ky tu chu cai tieng Viet theo dung thu tu huan luyen.
- Co ky tu 'đ', khong co cac ky tu 'f', 'j', 'w', 'z'.
- Su dung kieu tuple de dam bao bat bien (immutability) trong runtime.
- Chi so trong tuple chinh la nhan lop softmax cua model.
"""

from typing import Tuple

VIETNAMESE_ALPHABET: Tuple[str, ...] = (
    "a", "b", "c", "d", "đ", "e", "g", "h", "i", "k", "l", "m", "n",
    "o", "p", "q", "r", "s", "t", "u", "v", "x", "y"
)

NUM_CLASSES: int = len(VIETNAMESE_ALPHABET)

__all__ = ["VIETNAMESE_ALPHABET", "NUM_CLASSES"]
