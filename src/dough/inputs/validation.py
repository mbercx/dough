"""Schema-driven validation helpers.

All pydantic-touching code lives in this module so the rest of dough
stays pydantic-free at module import time.
"""

from __future__ import annotations

import functools
import typing

from pydantic import BaseModel, TypeAdapter
from pydantic.fields import FieldInfo

__all__ = ["validate_leaf"]


def validate_leaf(
    base_model: type[BaseModel], path: str, value: typing.Any
) -> typing.Any:
    """Validate `value` against the annotation of `path` on `base_model`.

    Walks the dotted `path` through nested pydantic submodels declared
    on `base_model`, picks the leaf field's annotation, and validates
    `value` against it via `TypeAdapter`. Returns the validated (and
    possibly coerced) value.

    Raises `KeyError` if the path does not resolve to a leaf field on
    the `base_model` (missing name, or walks into a non-submodel annotation).
    Raises `pydantic.ValidationError` if `value` does not match the
    leaf annotation.
    """
    *intermediate, leaf = path.split(".")

    models: list[type[BaseModel]] = [base_model]

    for name in intermediate:
        fields = [
            field
            for model in models
            if (field := model.model_fields.get(name)) is not None
        ]
        if not fields:
            names = ", ".join(m.__name__ for m in models)
            raise KeyError(f"{names} has no field {name!r} (in path {path!r})")

        submodels = [sub for field in fields for sub in get_field_models(field)]
        if not submodels:
            names = ", ".join(m.__name__ for m in models)
            raise KeyError(
                f"{names}.{name} is a leaf ({fields[0].annotation!r}); "
                f"cannot walk into it (in path {path!r})"
            )

        models = submodels

    leaf_fields = [
        field for model in models if (field := model.model_fields.get(leaf)) is not None
    ]
    if not leaf_fields:
        names = ", ".join(m.__name__ for m in models)
        raise KeyError(f"{names} has no field {leaf!r} (in path {path!r})")

    # Across union arms, validate against the union of each arm's leaf
    # annotation so e.g. a discriminator leaf accepts any arm's literal.
    annotation: typing.Any = typing.Union[
        tuple(
            typing.Annotated[(field.annotation, *field.metadata)]
            if field.metadata
            else field.annotation
            for field in leaf_fields
        )
    ]
    type_adapter = get_type_adapter(annotation)

    validated = type_adapter.validate_python(value)

    # Validation may coerce dicts into submodels (a single model, a list of
    # them, ...). Dump back through the same adapter to keep `_data` plain,
    # with `exclude_unset` so schema defaults do not leak into stored state.
    return type_adapter.dump_python(validated, exclude_unset=True)


def get_field_models(field: FieldInfo) -> list[type[BaseModel]]:
    """Find the pydantic models a field can hold.

    A field is usually one model, but a union field can be several. This
    looks through `Annotated`, `Optional`, and `Union` wrappers and
    returns every model inside. A plain (non-model) field returns an
    empty list.
    """

    def models_in(annotation: typing.Any) -> list[type[BaseModel]]:
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return [annotation]
        return [
            model for sub in typing.get_args(annotation) for model in models_in(sub)
        ]

    return models_in(field.annotation)


@functools.lru_cache(maxsize=None)
def get_type_adapter(annotation: typing.Any) -> TypeAdapter[typing.Any]:
    return TypeAdapter(annotation)
