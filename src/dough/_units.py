"""Unit metadata and pint integration for `dough`.

Houses the `Unit` marker users stack into `Annotated[...]` on output mappings,
plus the lazy pint registry used by `BaseOutput.get_output(to="pint")`.

`pint` is an optional dependency. Nothing in this module imports `pint` at
module load; the import is deferred to `get_ureg()`.
"""

from __future__ import annotations

import dataclasses
import functools
import typing

if typing.TYPE_CHECKING:
    import pint


@dataclasses.dataclass(frozen=True)
class Unit:
    """Marker attached in `Annotated[...]` to declare a field's physical unit.

    The string is consumed lazily by `pint.UnitRegistry().Quantity(value, unit)`
    when `to="pint"` is requested. It is **not** validated at decoration time —
    typos surface on first `to="pint"` call.
    """

    value: str


@functools.cache
def get_ureg() -> pint.UnitRegistry:
    """Return the shared pint `UnitRegistry`. Lazy import; cached singleton.

    Cached because pint Quantities from different registries do not interoperate
    (`q1 + q2` raises when their registries differ). All `to="pint"` calls share
    one registry. The `@functools.cache` also caches the `ImportError`, so a
    missing `pint` installation fails fast and once per process.
    """
    try:
        import pint

    except ImportError:
        raise ImportError(
            "pint required for to='pint'. Install: pip install dough[pint]"
        ) from None

    ureg = pint.UnitRegistry()
    ureg.define("Ha = hartree")
    return ureg
