"""Pytest fixtures shared by `dough`-based packages.

Opt in from a downstream package by adding
`pytest_plugins = ["dough.testing.plugin"]` to its top-level `conftest.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

import pytest

from ._serialize import _serialize

if TYPE_CHECKING:
    from pytest_regressions.data_regression import DataRegressionFixture


@pytest.fixture()
def json_serializer() -> Callable[..., Any]:
    """Make data JSON-serializable for regression tests.

    Usage::

        def test_something(json_serializer):
            json_serializer({"x": 1.0})
            json_serializer(big_list, max_number=50)
    """

    def factory(data: Any, max_number: int | None = None) -> Any:
        return _serialize(data, max_number=max_number)

    return factory


@pytest.fixture()
def robust_data_regression_check(
    data_regression: DataRegressionFixture,
    json_serializer: Callable[..., Any],
) -> Callable[..., Any]:
    """Run `data_regression.check` after making the data JSON-serializable."""

    def factory(data: Any, max_number: int | None = None) -> Any:
        return data_regression.check(json_serializer(data, max_number=max_number))

    return factory
