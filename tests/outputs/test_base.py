from textwrap import dedent
from typing import Annotated

from glom import Spec, T

import pytest
import yaml

from dough.converters.base import BaseConverter
from dough.outputs.base import BaseOutput, output_mapping


# =============================================================================
# Reused fixture classes
# =============================================================================


class _DoubleConverter(BaseConverter):
    """Trivial `BaseConverter` subclass that doubles scalar values.

    `BaseOutput.get_output` checks the guard with the short key (`"c"`) but
    calls `convert()` with the dotted key (`"nested.c"`), so both must be
    registered for submapping dispatch to work.
    """

    @classmethod
    def get_conversion_mapping(cls):
        entry = (lambda x: x * 2, T)
        return {"A": entry, "c": entry, "nested.c": entry}


@output_mapping
class _NestedMapping:
    c: Annotated[int, Spec("b.c")]
    d: Annotated[int, Spec("b.d")]
    missing: Annotated[int, Spec("b.nope")]


@output_mapping
class _TestMapping:
    A: Annotated[float, Spec("a")]
    unmapped: Annotated[int, Spec("b.c")]
    not_parsed: Annotated[str, Spec("e")]
    nested: _NestedMapping


class _TestOutput(BaseOutput[_TestMapping]):
    converters = {"double": _DoubleConverter}

    @classmethod
    def from_dir(cls, _: str):
        pass


# =============================================================================
# Shared raw_outputs fixture
# =============================================================================


@pytest.fixture
def raw_outputs():
    """Simple `raw_outputs` for transparent testing."""
    return yaml.safe_load(
        dedent(
            """
            a: 1
            b:
                c: 3
                d: 4
            """
        )
    )


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.parametrize(
    ("spec", "result"),
    [
        ("a", 1),
        ("b.c", 3),
        ("b", {"c": 3, "d": 4}),
    ],
)
def test_get_output_from_spec(raw_outputs, spec, result):
    assert result == _TestOutput(raw_outputs).get_output_from_spec(spec)


def test_list_outputs(raw_outputs):
    assert _TestOutput(raw_outputs).list_outputs() == ["A", "unmapped", "nested"]
    assert _TestOutput(raw_outputs).list_outputs(only_available=False) == [
        "A",
        "unmapped",
        "not_parsed",
        "nested",
    ]


def test_outputs_unavailable_raises(raw_outputs):
    outputs = _TestOutput(raw_outputs).outputs
    with pytest.raises(AttributeError, match="not_parsed.*not available"):
        outputs.not_parsed


def test_outputs_frozen(raw_outputs):
    outputs = _TestOutput(raw_outputs).outputs
    with pytest.raises(AttributeError):
        outputs.A = 999


def test_get_output_dict(raw_outputs):
    assert _TestOutput(raw_outputs).get_output_dict() == {
        "A": 1,
        "unmapped": 3,
        "nested": {"c": 3, "d": 4},
    }
    assert _TestOutput(raw_outputs).get_output_dict(["A"]) == {"A": 1}
    with pytest.raises(KeyError):
        _TestOutput(raw_outputs).get_output_dict(["B"])


# --- SubMapping (nested output namespaces) ----------------------------------


def test_submapping_output_access(raw_outputs):
    """Resolved outputs on a sub-namespace are accessible via attribute."""
    outputs = _TestOutput(raw_outputs).outputs
    assert outputs.nested.c == 3
    assert outputs.nested.d == 4


def test_submapping_missing_output_raises(raw_outputs):
    outputs = _TestOutput(raw_outputs).outputs
    with pytest.raises(AttributeError, match="missing.*not available"):
        outputs.nested.missing


def test_submapping_get_output_namespace_returns_dict(raw_outputs):
    """`get_output(<sub-namespace>)` returns a partial dict of available outputs."""
    out = _TestOutput(raw_outputs)
    assert out.get_output("nested") == {"c": 3, "d": 4}
    # Users index the dict directly.
    assert out.get_output("nested")["c"] == 3


def test_decorator_rejects_bare_annotation_non_output_mapping():
    """Bare annotation whose type isn't `@output_mapping`-decorated is rejected at decoration time."""
    with pytest.raises(TypeError, match="bad.*@output_mapping class"):

        @output_mapping
        class _BadBare:
            bad: int


def test_decorator_rejects_annotated_without_spec():
    """`Annotated[T, ...]` without a `Spec` is rejected at decoration time."""
    with pytest.raises(TypeError, match="bad.*Annotated"):

        @output_mapping
        class _BadAnn:
            bad: Annotated[int, "not a spec"]


def test_decorator_rejects_multiple_specs():
    """Multiple `Spec` entries in one `Annotated` raise `TypeError`."""
    with pytest.raises(TypeError, match="multiple Spec entries"):

        @output_mapping
        class _BadMulti:
            bad: Annotated[int, Spec("x"), Spec("y")]


def test_base_init_rejects_non_annotated_non_submapping_default():
    """Non-Annotated field with a plain default (not a `SubMapping`) raises in `__init__`."""

    @output_mapping
    class _BadParent:
        # Escapes decorator injection (has a default), then trips the `build`
        # guard at instantiation because it's neither Annotated[T, Spec] nor a
        # SubMapping default.
        bad: int = 42  # type: ignore[assignment]

    class _BadOutput(BaseOutput[_BadParent]):
        @classmethod
        def from_dir(cls, _: str):
            pass

    with pytest.raises(TypeError, match="_BadParent.bad"):
        _BadOutput(raw_outputs={})


# --- Fallback defaults on Annotated fields ------------------------------------


@output_mapping
class _DefaultsMapping:
    """Mapping with an explicit fallback default on an unparsed field."""

    parsed: Annotated[int, Spec("a")]
    unparsed_default: Annotated[bool, Spec("missing.path")] = False
    unparsed_no_default: Annotated[str, Spec("other.missing")]


class _DefaultsOutput(BaseOutput[_DefaultsMapping]):
    @classmethod
    def from_dir(cls, _: str):
        pass


def test_explicit_default_is_reachable(raw_outputs):
    """Fallback default is returned when the Spec doesn't resolve."""
    outputs = _DefaultsOutput(raw_outputs).outputs
    assert outputs.parsed == 1
    assert outputs.unparsed_default is False


def test_unparsed_without_default_raises(raw_outputs):
    """Unparsed field with no explicit default still raises."""
    outputs = _DefaultsOutput(raw_outputs).outputs
    with pytest.raises(AttributeError, match="unparsed_no_default.*not available"):
        outputs.unparsed_no_default


def test_explicit_default_not_in_list_outputs(raw_outputs):
    """Fallback default doesn't count as 'available' — field is not listed."""
    assert _DefaultsOutput(raw_outputs).list_outputs() == ["parsed"]


# --- __dir__ on output mapping instances --------------------------------------


def test_dir_only_lists_resolved_fields(raw_outputs):
    """`dir()` on a mapping instance excludes fields still holding sentinels."""
    outputs = _TestOutput(raw_outputs).outputs
    visible = dir(outputs)
    assert "A" in visible
    assert "not_parsed" not in visible


def test_dir_includes_fields_with_fallback_default(raw_outputs):
    """Fallback defaults are real values, so `dir()` lists them."""
    outputs = _DefaultsOutput(raw_outputs).outputs
    visible = dir(outputs)
    assert "parsed" in visible
    assert "unparsed_default" in visible
    assert "unparsed_no_default" not in visible


# --- _get_mapping_class error path -------------------------------------------


def test_init_raises_without_generic_parameter():
    """Subclass that omits the generic `[T]` parameter raises `TypeError`."""

    class _Bare(BaseOutput):  # type: ignore[type-arg]
        @classmethod
        def from_dir(cls, _: str):
            pass

    with pytest.raises(TypeError, match="must subclass BaseOutput"):
        _Bare(raw_outputs={})


# --- get_output with converter (to=...) --------------------------------------


def test_get_output_with_converter(raw_outputs):
    """`get_output(name, to=...)` applies the converter when available."""
    assert _TestOutput(raw_outputs).get_output("A", to="double") == 2  # 1 * 2


def test_get_output_without_matching_converter_passes_through(raw_outputs):
    """When the converter mapping doesn't cover the name, return raw value."""
    assert _TestOutput(raw_outputs).get_output("unmapped", to="double") == 3  # raw b.c


def test_get_output_unsupported_converter_raises(raw_outputs):
    """`get_output(name, to='bad')` raises `ValueError` listing available converters."""
    with pytest.raises(ValueError, match="not supported.*double"):
        _TestOutput(raw_outputs).get_output("A", to="bad")


def test_get_output_submapping_with_converter(raw_outputs):
    """Converter applied per sub-field when the output is a submapping dict."""
    # "nested.c" is in conversion_mapping -> doubled; "nested.d" is not -> raw
    assert _TestOutput(raw_outputs).get_output("nested", to="double") == {
        "c": 6,
        "d": 4,
    }


# --- Boundary / edge-case tests ----------------------------------------------


def test_get_output_nonexistent_name_raises(raw_outputs):
    """`get_output('nonexistent')` raises `KeyError` when name is not in mapping."""
    with pytest.raises(KeyError):
        _TestOutput(raw_outputs).get_output("nonexistent")


def test_submapping_all_specs_fail():
    """Submapping where every sub-spec fails glom returns an empty dict."""
    assert _TestOutput({"x": 1}).get_output("nested") == {}


def test_get_output_to_with_empty_converters_raises(raw_outputs):
    """`get_output(name, to='x')` raises `ValueError` when `converters` is empty."""

    @output_mapping
    class _M:
        A: Annotated[float, Spec("a")]

    class _Out(BaseOutput[_M]):
        converters = {}

        @classmethod
        def from_dir(cls, _: str):
            pass

    with pytest.raises(ValueError, match="not supported"):
        _Out(raw_outputs).get_output("A", to="x")


def test_get_output_dict_with_converter(raw_outputs):
    """`get_output_dict(to=...)` applies the converter per-output, passes through unmapped names."""
    assert _TestOutput(raw_outputs).get_output_dict(to="double") == {
        "A": 2,
        "unmapped": 3,
        "nested": {"c": 6, "d": 4},
    }


def test_converter_exception_propagates(raw_outputs):
    """An exception raised inside `convert()` propagates to the caller."""

    def _boom(_):
        raise RuntimeError("converter exploded")

    class _BrokenConverter(BaseConverter):
        @classmethod
        def get_conversion_mapping(cls):
            return {"A": (_boom, T)}

    @output_mapping
    class _M:
        A: Annotated[float, Spec("a")]

    class _Out(BaseOutput[_M]):
        converters = {"broken": _BrokenConverter}

        @classmethod
        def from_dir(cls, _: str):
            pass

    with pytest.raises(RuntimeError, match="converter exploded"):
        _Out(raw_outputs).get_output("A", to="broken")
