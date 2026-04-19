"""Abstract base class for code outputs."""

from __future__ import annotations

import abc
import contextlib
import dataclasses
import typing
from functools import cached_property
from typing import Annotated

from glom import glom, GlomError, Spec

from dough.converters.base import BaseConverter


T = typing.TypeVar("T")
TC = typing.TypeVar("TC", bound=type)


_NOT_PARSED = object()
"""Sentinel marking a field whose `Spec` was not resolved against `raw_outputs`.

Installed by `@output_mapping` as the dataclass default for every
`Annotated[T, Spec(...)]` field that does not declare an explicit default.
`__getattribute__` raises on this sentinel; explicit defaults (e.g. `= False`)
are left untouched and reachable normally.
"""


class SubMapping:
    """Sentinel marking a field as a nested output mapping.

    `BaseOutput` resolves these at instantiation time. Nesting is intended to
    be one level only: a sub-mapping class should only contain `Spec` fields.
    """

    def __init__(self, mapping_cls: type):
        self.mapping_cls = mapping_cls


def _spec_from_annotated(hint: typing.Any) -> Spec | None:
    """Return the `Spec` embedded in an `Annotated[...]` type hint, or `None`.

    Raises `TypeError` if multiple `Spec` entries are present.
    """
    if typing.get_origin(hint) is not Annotated:
        return None
    specs = [arg for arg in typing.get_args(hint)[1:] if isinstance(arg, Spec)]
    if not specs:
        return None
    if len(specs) > 1:
        raise TypeError(f"Annotated type has multiple Spec entries: {hint!r}")
    return specs[0]


def output_mapping(cls: TC) -> TC:
    """Decorator that defines a typed, frozen output mapping for a code.

    Each field on the decorated class becomes one output of the corresponding
    `BaseOutput` subclass. There are two kinds of fields:

    **Parse-target fields** — a quantity extracted from `raw_outputs` via glom.
    Declared as `Annotated[T, Spec(...)]`, with a docstring stating units:

        fermi_energy: Annotated[float, Spec("xml.output.band_structure.fermi_energy")]
        \"""Fermi energy in eV.\"""

    If the `Spec` fails to resolve, accessing the field on the `outputs`
    namespace raises `AttributeError`. Attach an explicit default to return
    that value instead when parsing fails:

        job_done: Annotated[bool, Spec("stdout.job_done")] = False
        \"""Whether the job completed. Defaults to False if not parsed.\"""

    **Sub-namespace fields** — a nested group of outputs. Declared as a bare
    annotation whose type is another `@output_mapping` class:

        parameters: _ParametersMapping
        \"""Parameters the calculation ran with.\"""

    Sub-namespace classes must be defined before the parent that references
    them, and should themselves only contain parse-target fields (one level of
    nesting).

    The decorator applies `@dataclass(frozen=True)`, so parsed outputs are
    immutable. `dir()` on a mapping instance lists only the fields that
    actually resolved, for clean tab completion.
    """

    def __getattribute__(self: typing.Any, name: str) -> typing.Any:
        value = object.__getattribute__(self, name)
        if value is _NOT_PARSED or isinstance(value, SubMapping):
            raise AttributeError(f"'{name}' is not available in the parsed outputs.")
        return value

    def __dir__(self: typing.Any) -> list[str]:
        return [
            name
            for name, value in self.__dict__.items()
            if value is not _NOT_PARSED and not isinstance(value, SubMapping)
        ]

    setattr(cls, "__getattribute__", __getattribute__)
    setattr(cls, "__dir__", __dir__)

    # Inject dataclass defaults so that mapping instances can be constructed
    # without supplying every field — the `outputs` cached_property only passes
    # kwargs for fields that resolved, and the rest must come from defaults.
    #
    # Parse-target fields (`Annotated[T, Spec(...)]`) without an explicit
    # fallback get `_NOT_PARSED`, which `__getattribute__` traps to raise a
    # clear "not available" error. Fields with an explicit fallback are left
    # alone — the explicit value is returned directly when the Spec fails.
    #
    # Sub-namespace fields (bare `_OtherMapping`) get a `SubMapping(hint)`
    # placeholder; the `outputs` builder always replaces it with an
    # instantiated sub-mapping, so it never reaches user code.
    #
    # Note: `get_type_hints` evaluates annotations; modules that use
    # `from __future__ import annotations` together with `TYPE_CHECKING`-only
    # sub-mapping imports would raise `NameError` here. Sub-mapping classes
    # must be defined *before* the parent that references them.
    hints = typing.get_type_hints(cls, include_extras=True)
    for name, hint in hints.items():
        if hasattr(cls, name):  # already has a default
            continue

        spec = _spec_from_annotated(hint)

        if spec is not None:
            setattr(cls, name, _NOT_PARSED)
            continue

        if isinstance(hint, type) and getattr(hint, "_is_output_mapping", False):
            setattr(cls, name, SubMapping(hint))
            continue

        raise TypeError(
            f"{cls.__name__}.{name}: needs an `Annotated[T, Spec(...)]` annotation "
            f"(optionally with a fallback default), or a bare annotation whose type "
            f"is an @output_mapping class (which must be defined before this class)"
        )

    setattr(cls, "_is_output_mapping", True)
    return dataclasses.dataclass(frozen=True)(cls)  # type: ignore[return-value]


class BaseOutput(abc.ABC, typing.Generic[T]):
    """Abstract base class for code outputs."""

    converters: typing.ClassVar[dict[str, type[BaseConverter]]] = {}
    """Mapping of target-library name to its `BaseConverter` subclass.

    Subclasses populate this with the converters they support, e.g.

        `converters = {"ase": ASEConverter, ...}`

    Each converter is responsible for importing optional dependencies lazily inside the
    `get_conversion_mapping()` classmethod, so simply listing it here does not pull it
    in at import time.
    """

    @classmethod
    def _get_mapping_class(cls) -> type:
        """Extract the mapping class from the generic parameter.

        Example: PwOutput(BaseOutput[_PwMapping]) → _PwMapping
        """
        for base in getattr(cls, "__orig_bases__", []):
            if typing.get_origin(base) is BaseOutput and (
                args := typing.get_args(base)
            ):
                return args[0]  # type: ignore[no-any-return]
        raise TypeError(
            f"{cls.__name__} must subclass BaseOutput[T] with a decorated output mapping, "
            "e.g. class PwOutput(BaseOutput[_PwMapping])"
        )

    def __init__(self, raw_outputs: dict[str, typing.Any]) -> None:
        self.raw_outputs = raw_outputs

        def build(mapping_cls: type) -> dict[str, typing.Any]:
            """Build the nested spec dict from a mapping class."""

            result: dict[str, typing.Any] = {}
            hints = typing.get_type_hints(mapping_cls, include_extras=True)

            for field in dataclasses.fields(mapping_cls):
                hint = hints[field.name]
                spec = _spec_from_annotated(hint)

                if spec is not None:
                    result[field.name] = spec
                elif isinstance(field.default, SubMapping):
                    result[field.name] = build(field.default.mapping_cls)
                else:
                    raise TypeError(
                        f"{mapping_cls.__name__}.{field.name}: expected an "
                        f"`Annotated[T, Spec(...)]` annotation or a `SubMapping` "
                        f"default, got {field.default!r}"
                    )

            return result

        self._output_spec_mapping = build(self._get_mapping_class())

    @classmethod
    @abc.abstractmethod
    def from_dir(cls, directory: str) -> BaseOutput[T]:
        pass  # pragma: no cover

    def get_output_from_spec(self, spec: typing.Any) -> typing.Any:
        """Return a value from `raw_outputs` using a glom specification.

        Args:
            spec: A glom specification describing the path/transforms to apply.

        Raises:
            GlomError: If the specification is invalid or the path cannot be resolved.
        """
        return glom(self.raw_outputs, spec)

    def get_output(self, name: str, to: str | None = None) -> typing.Any:
        """Return an output by `name`.

        Args:
            name (str): Output to retrieve (e.g., "structure", "fermi_energy",
                "forces").
            to (str): Optional target library to convert the base output to.

                The supported values are the keys of this subclass's `converters`
                class variable — list them with

                    `sorted(OutputClass.converters)`

                Passing an unsupported value raises `ValueError` listing the
                available options.

        Examples:
            >>> pw_out.get_output(name="structure")
            >>> pw_out.get_output(name="structure", to="pymatgen")
        """
        entry = self._output_spec_mapping[name]

        if isinstance(entry, dict):
            output_data: typing.Any = {}

            for sub_name, sub_spec in entry.items():
                with contextlib.suppress(GlomError):
                    output_data[sub_name] = glom(self.raw_outputs, sub_spec)
        else:
            output_data = glom(self.raw_outputs, entry)

        if to is None:
            return output_data

        try:
            Converter = self.converters[to]
        except KeyError:
            available = sorted(self.converters)
            raise ValueError(
                f"Library '{to}' is not supported. Available: {available}"
            ) from None

        conversion_mapping = Converter.get_conversion_mapping()

        if isinstance(entry, dict):
            return {
                sub_name: Converter().convert(f"{name}.{sub_name}", sub_value)
                if sub_name in conversion_mapping
                else sub_value
                for sub_name, sub_value in output_data.items()
            }

        return (
            Converter().convert(name, output_data)
            if name in conversion_mapping
            else output_data
        )

    def get_output_dict(
        self,
        names: None | list[str] = None,
        to: str | None = None,
    ) -> dict[str, typing.Any]:
        """Return a dictionary of outputs.

        Args:
            names (list[str]): Output names to include. If not provided, all
                available outputs are included.
            to (str): Optional target library to convert the base output to.

                The supported values are the keys of this subclass's `converters`
                class variable — list them with

                    `sorted(OutputClass.converters)`

                Passing an unsupported value raises `ValueError` listing the
                available options.

        Returns:
            dict: Mapping from output name to value.
        """
        names = names or self.list_outputs()
        return {name: self.get_output(name, to=to) for name in names}

    def list_outputs(self, only_available: bool = True) -> list[str]:
        """List the output names.

        Args:
            only_available (bool, default True): Include only outputs that are
                available, i.e. produced by the calculation and successfully parsed. If
                False, list all outputs that this parser supports.

        Returns:
            list[str]: A list of output names.
        """
        if not only_available:
            return list(self._output_spec_mapping.keys())

        output_names = []

        for name in self._output_spec_mapping.keys():
            try:
                self.get_output(name)
            except GlomError:
                continue
            else:
                output_names.append(name)

        return output_names

    @cached_property
    def outputs(self) -> T:
        """Namespace with available outputs."""

        def build(mapping_cls: type, data: dict[str, typing.Any]) -> typing.Any:
            defaults = {f.name: f.default for f in dataclasses.fields(mapping_cls)}
            kwargs = {}

            for name, default in defaults.items():
                if isinstance(default, SubMapping):
                    kwargs[name] = build(default.mapping_cls, data.get(name, {}))
                elif name in data:
                    kwargs[name] = data[name]

            return mapping_cls(**kwargs)

        return build(self._get_mapping_class(), self.get_output_dict())  # type: ignore[no-any-return]
