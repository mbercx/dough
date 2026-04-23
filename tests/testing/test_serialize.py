"""Tests for `dough.testing._serialize` helpers."""

from __future__ import annotations

import numpy as np
import pytest

from dough.testing._serialize import _get_equally_spaced, _serialize


# --- _serialize ---


def test_serialize_str_passthrough():
    assert _serialize("abc") == "abc"


def test_serialize_bool_passthrough():
    assert _serialize(True) is True
    assert _serialize(False) is False


def test_serialize_int_rounded_to_float():
    assert _serialize(3) == 3.0
    assert isinstance(_serialize(3), float)


def test_serialize_float_rounded_to_five_digits():
    assert _serialize(1.123456789) == 1.12346


def test_serialize_list_recursed():
    assert _serialize([1, 2.5, "x"]) == [1.0, 2.5, "x"]


def test_serialize_tuple_becomes_list():
    assert _serialize((1, 2)) == [1.0, 2.0]


def test_serialize_dict_recursed_on_values():
    assert _serialize({"a": 1, "b": [2.0]}) == {"a": 1.0, "b": [2.0]}


def test_serialize_ndarray_tolist():
    assert _serialize(np.array([1.0, 2.0, 3.0])) == [1.0, 2.0, 3.0]


def test_serialize_complex_ndarray_split():
    arr = np.array([1 + 2j, 3 + 4j])
    assert _serialize(arr) == [[1.0, 3.0], [2.0, 4.0]]


def test_serialize_np_integer_rounded():
    assert _serialize(np.int64(3)) == 3.0


def test_serialize_np_floating_rounded():
    assert _serialize(np.float64(1.123456789)) == 1.12346


def test_serialize_list_subsampled():
    data = list(range(10))
    assert _serialize(data, max_number=3) == [0.0, 4.0, 9.0]


def test_serialize_ndarray_subsampled():
    arr = np.arange(10, dtype=float)
    assert _serialize(arr, max_number=3) == [0.0, 4.0, 9.0]


def test_serialize_unsupported_type_raises():
    with pytest.raises(TypeError, match="not supported"):
        _serialize(object())


# --- _get_equally_spaced ---


def test_get_equally_spaced_empty_returns_empty():
    assert _get_equally_spaced([], 1) == []


def test_get_equally_spaced_single_element_returned():
    assert _get_equally_spaced([42], 1) == [42]


def test_get_equally_spaced_indices():
    assert _get_equally_spaced(list(range(10)), 3) == [0, 4, 9]


def test_get_equally_spaced_tuple_input_returns_list():
    assert _get_equally_spaced((10, 20, 30, 40, 50), 3) == [10, 30, 50]
