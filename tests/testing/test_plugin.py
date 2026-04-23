"""Tests for the `dough.testing` pytest plugin fixtures."""

from __future__ import annotations


def test_json_serializer_fixture_serializes(json_serializer):
    assert json_serializer({"a": 1.123456789}) == {"a": 1.12346}


def test_json_serializer_fixture_subsamples(json_serializer):
    assert json_serializer(list(range(10)), max_number=3) == [0.0, 4.0, 9.0]


def test_robust_data_regression_check_accepts_max_number(robust_data_regression_check):
    robust_data_regression_check({"xs": list(range(100))}, max_number=5)
