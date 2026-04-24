"""Tests for `dough._units`: the `Unit` marker and pint registry."""

from __future__ import annotations

import dataclasses
import sys

import pytest

from dough import Unit
from dough._units import get_ureg


# =============================================================================
# Unit dataclass
# =============================================================================


def test_unit_value_stored():
    assert Unit("eV").value == "eV"


def test_unit_equality_by_value():
    assert Unit("eV") == Unit("eV")
    assert Unit("eV") != Unit("Ha")


def test_unit_repr_shows_value():
    assert repr(Unit("eV")) == "Unit(value='eV')"


def test_unit_is_frozen():
    u = Unit("eV")
    with pytest.raises(dataclasses.FrozenInstanceError):
        u.value = "Ha"  # type: ignore[misc]


# =============================================================================
# get_ureg
# =============================================================================


def test_get_ureg_returns_registry_singleton():
    r1 = get_ureg()
    r2 = get_ureg()
    assert r1 is r2


def test_get_ureg_quantities_interop():
    ureg = get_ureg()
    q1 = ureg.Quantity(1.0, "eV")
    q2 = ureg.Quantity(2.0, "eV")
    total = q1 + q2
    assert total.magnitude == pytest.approx(3.0)
    assert str(total.units) == "electron_volt"


def test_get_ureg_raises_when_pint_missing(monkeypatch):
    get_ureg.cache_clear()
    monkeypatch.setitem(sys.modules, "pint", None)
    with pytest.raises(ImportError, match=r"pip install dough\[pint\]"):
        get_ureg()
    get_ureg.cache_clear()
