# Units

This page documents `dough`'s per-field unit mechanism and the `to="pint"` conversion target.
It is the mechanism doc; opinionated unit-choice policy (which SSOT unit a given wrapper picks for energy, forces, etc.) lives in the wrapper package's own docs.

## The `Unit` marker

Unit information attaches to a field as an additional `Annotated[...]` argument, alongside `Spec`:

```python
@output_mapping
class _MyMapping:
    total_energy: Annotated[float, Spec("xml.energy"), Unit("eV")]
    """Total energy in eV."""
```

`Unit` is a frozen dataclass.
The string is stored as-is and is **not** validated at decoration time — typos surface on first `to="pint"` call.
A pre-commit lint that imports `pint` and validates unit strings is planned separately.

The docstring on the field is the human-facing source of truth for the unit.
`Unit(...)` is the machine-readable companion, used only for `to="pint"` conversion.
The two are redundant by design: prose for readers and doc generators, a structured marker for runtime wrapping.

## The `to="pint"` target

`BaseOutput.get_output(name, to="pint")` returns a `pint.Quantity` for numeric fields that carry a `Unit` marker, and the raw value for everything else:

| Field shape                                    | Returned value                                         |
|------------------------------------------------|--------------------------------------------------------|
| Numeric (scalar/ndarray), `Unit` marker        | `ureg.Quantity(value, unit)`                           |
| Numeric, no `Unit` marker                      | raw value (pass-through)                               |
| Non-numeric (str, bool, ...)                   | raw value (pass-through)                               |
| Sub-mapping field                              | dict of per-sub-field results, applying rules above    |

`get_output_dict(to="pint")` iterates fields and never raises due to partial coverage — the returned dict is mixed (`Quantity` + raw).

The pint registry is imported lazily on first call and cached as a singleton.
All `to="pint"` calls share one registry so the returned `Quantity` objects interoperate under arithmetic.
If `pint` is not installed, the first call raises `ImportError` with the install hint `pip install dough[pint]`.

## The `to=` contract

`to="pint"` is intentionally shaped to **parallel the existing library converters** (`to="ase"`, `to="pymatgen"`, `to="aiida"`).
Same rule: *convert if possible, pass through the raw value if not*.

Users learn one rule for the whole `to=` argument:

> `get_output(name, to=X)` asks "give me this output as X, or the base value if X doesn't apply to this field."

### Why not `to="Ha"` or `to="eV"`?

Overloading `to=` with unit names was rejected.
It mixes two different kinds of target — library shape (`"ase"`) and unit target (`"Ha"`) — under one slot, and forces `dough` to reimplement or thinly wrap pint's unit parsing for no gain.
Users who want a different unit chain off the returned `Quantity`: `out.get_output("energy", to="pint").to("Ha")`.

### Why not a separate `unit=` kwarg?

A separate `unit=` argument was rejected for the same reason.
It would force `dough` to implement dimensional checking, unit compatibility, and the conversion math — all of which already live in pint.
The two-step `to="pint"` + `.to("...")` is strictly more explicit at the call site and pushes validation into pint where it belongs.

### Why not drop `to="pint"` and make users wrap values themselves?

Every caller would then need to know the pint import dance, handle fields without markers, and write the `Quantity(...)` wrap by hand.
That boilerplate belongs in `dough`.

## Composition with library converters

`to="pint"` and `to="pymatgen"` / `to="ase"` / `to="aiida"` are **mutually exclusive per call** today.
A user who wants `get_output_dict()` to return pymatgen `Structure` objects **and** pint `Quantity` scalars in one dict must make two calls and merge.

This is a known limitation shipped on purpose.
`to="pint"` satisfies the immediate need (introspect a unit; convert a scalar) without complicating the API before composition is actually requested.

### Planned extension — tuple of targets

When users ask for combined shape + unit in one call, `to=` will extend to accept a tuple:

```python
out.get_output_dict(to=("pymatgen", "pint"))
```

Semantics: try each target left-to-right, first one that applies wins.
Single-string `to="pint"` becomes `to=("pint",)` under the hood, so the extension is a strict superset of today's API with zero breaking change.
The "applies" signal is that a converter returns a value different from the raw input; pint applies when a `Unit` marker is present and the value is numeric; library converters apply when the field name is listed in their `conversion_mapping`.

User-facing behavior on conflict fields (e.g. `forces` with both a `Unit` marker and a pymatgen conversion) is controlled by tuple order: `("pymatgen", "pint")` gives pymatgen shapes; `("pint", "pymatgen")` gives a `Quantity`-wrapped array.

## Installing `pint`

`pint` is an optional dependency:

```bash
pip install dough[pint]
```

Nothing in `dough` imports `pint` at module load.
The import is deferred to the first `to="pint"` call.
