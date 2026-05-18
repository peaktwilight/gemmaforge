"""CPU-only tests for probe scan scoring helpers."""

from __future__ import annotations

import numpy as np
import pytest

from integrations.pwnkit.adapter import _token_windows, _topk_mean


def test_token_windows_covers_long_input_with_overlap():
    ids = list(range(10))
    windows = _token_windows(ids, max_tokens=4, stride=2)
    assert windows == [
        (0, [0, 1, 2, 3]),
        (2, [2, 3, 4, 5]),
        (4, [4, 5, 6, 7]),
        (6, [6, 7, 8, 9]),
    ]


def test_token_windows_short_input_single_window():
    assert _token_windows([1, 2, 3], max_tokens=8, stride=4) == [(0, [1, 2, 3])]


def test_token_windows_validates_positive_budget():
    with pytest.raises(ValueError):
        _token_windows([1], max_tokens=0, stride=1)
    with pytest.raises(ValueError):
        _token_windows([1], max_tokens=1, stride=0)


def test_topk_mean_is_less_spiky_than_max():
    vals = np.array([0.1, 0.2, 0.3, 0.99], dtype=float)
    assert _topk_mean(vals, min_k=3, frac=0.02) == pytest.approx((0.2 + 0.3 + 0.99) / 3)
    assert _topk_mean(vals, min_k=1, frac=0.02) == pytest.approx(0.99)
