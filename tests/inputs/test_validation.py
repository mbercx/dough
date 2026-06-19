"""Tests for the schema-driven leaf validator."""

from __future__ import annotations

import typing

import pytest
from pydantic import BaseModel, Field, ValidationError

from dough.inputs.validation import validate_leaf


class Basis(BaseModel):
    ecut: float = Field(gt=0)


class Calculation(BaseModel):
    type: str
    spin: str = "none"


class ListCard(BaseModel):
    kind: typing.Literal["tpiba", "crystal"] = "tpiba"
    points: list[float] = []


class GridCard(BaseModel):
    kind: typing.Literal["automatic"] = "automatic"
    grid: tuple[int, int, int]


KCard = typing.Annotated[typing.Union[ListCard, GridCard], Field(discriminator="kind")]


class InputModel(BaseModel):
    calculation: Calculation
    basis: Basis
    optional_section: Basis | None = None
    k_points: KCard = Field(default=ListCard(), discriminator="kind")


def test_validates_top_level_leaf():
    assert validate_leaf(InputModel, "calculation.type", "relax") == "relax"


def test_coerces_via_type_adapter():
    assert validate_leaf(InputModel, "basis.ecut", "3.5") == 3.5


def test_submodel_write_returns_plain_dict():
    """Coercion of a dict into `Basis` is dumped back to a plain dict, so no
    pydantic model leaks into `_data`."""
    result = validate_leaf(InputModel, "basis", {"ecut": 30.0})
    assert result == {"ecut": 30.0}
    assert not isinstance(result, BaseModel)


def test_submodel_write_excludes_unset_defaults():
    """`Calculation.spin` defaults to "none"; writing only `type` must not leak
    the default into the stored dict."""
    assert validate_leaf(InputModel, "calculation", {"type": "scf"}) == {"type": "scf"}


def test_rejects_wrong_type():
    with pytest.raises(ValidationError):
        validate_leaf(InputModel, "calculation.type", 42)


def test_rejects_field_constraint_violation():
    with pytest.raises(ValidationError):
        validate_leaf(InputModel, "basis.ecut", -1.0)


def test_walks_through_optional_union():
    # `Basis | None` -> walker picks the `Basis` branch and descends.
    assert validate_leaf(InputModel, "optional_section.ecut", 30.0) == 30.0


def test_discriminator_leaf_accepts_any_arm_literal():
    # `kind` is the discriminator; "automatic" lives only on GridCard.
    assert validate_leaf(InputModel, "k_points.kind", "automatic") == "automatic"
    assert validate_leaf(InputModel, "k_points.kind", "tpiba") == "tpiba"


def test_arm_specific_leaf_resolves_to_owning_arm():
    # `grid` exists only on GridCard, not the first union arm.
    assert validate_leaf(InputModel, "k_points.grid", (4, 4, 4)) == (4, 4, 4)


def test_discriminated_union_rejects_unknown_kind():
    with pytest.raises(ValidationError):
        validate_leaf(InputModel, "k_points.kind", "bogus")


def test_missing_intermediate_field_raises_keyerror():
    with pytest.raises(KeyError, match="bogus"):
        validate_leaf(InputModel, "bogus.x", 1)


def test_missing_leaf_field_raises_keyerror():
    with pytest.raises(KeyError, match="bogus"):
        validate_leaf(InputModel, "calculation.bogus", 1)


def test_walking_into_leaf_raises_keyerror():
    with pytest.raises(KeyError, match="leaf"):
        validate_leaf(InputModel, "basis.ecut.subfield", 1)
