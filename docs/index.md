# `dough`

*Roll your own typed wrapper.*

!!! warning

    `dough` is still pre-1.0. The API is still evolving and can break in minor releases.

`dough` is a small framework for building typed Python wrappers around the output files of simulation codes.
It ships the generic machinery — file parsers, declarative output mappings, optional library converters — and stays out of the way of the code-specific details.
Code-specific wrappers live in their own packages (see [Packages built on `dough`](#packages-built-on-dough) below).

## 📦 Installation

Wrapper packages declare `dough` as a runtime dependency in their own `pyproject.toml`:

```toml
[project]
dependencies = [
    "dough>=0.3",
]
```

For ad-hoc exploration you can of course also just install it directly:

```bash
pip install dough
```

## 🌯 The current layers

- **Parsers** — turn one output file into a plain dict. One parser per file format; stateless, with a single `parse(content)` method.
- **Output mappings** — frozen dataclasses whose fields are `Annotated[T, Spec(...)]`. Each field declares the output's name, type, unit (in its docstring), and how to extract it from the parsed dicts via a [`glom`](https://glom.readthedocs.io/) `Spec`. One source of truth per quantity.
- **Converters** — optional adapters that turn base Python outputs into `ase`, `pymatgen`, or `aiida-core` objects. Heavy third-party imports stay lazy so wrapper packages don't pay for them at import time.

See the [outputs design page](design/outputs.md) for the full picture.

## ✨ A minimal example

Declare the outputs as `Annotated[T, Spec(...)]` fields on an `@output_mapping` class, then bind it to a `BaseOutput` subclass:

```python
from typing import Annotated
from dough.outputs import BaseOutput, output_mapping
from glom import Spec


@output_mapping
class _MyMapping:
    fermi_energy: Annotated[float, Spec("xml.output.band_structure.fermi_energy")]
    """Fermi energy in eV."""


class MyOutput(BaseOutput[_MyMapping]):
    ...
```

Each subclass implements `from_dir` (and/or `from_files`) to wire in its parsers.
Once instantiated, the declared fields are reachable as a typed namespace:

```python
my_out = MyOutput.from_dir("/path/to/run_dir")
my_out.outputs.fermi_energy  # -> float
```

## ⚖️ Units and pint

Stack a `Unit` marker to label a field's physical unit:

```python
@output_mapping
class _MyMapping:
    total_energy: Annotated[float, Spec("energy"), Unit("eV")]
    xc_functional: Annotated[str, Spec("xc")]
```

Users can obtain a [`pint`](https://pint.readthedocs.io/) `Quantity` when reading the output:

```python
out.get_output("total_energy")             # 6.23
out.get_output("total_energy", to="pint")  # <Quantity(6.23, 'eV')>
out.get_output("total_energy", to="pint").to("Ha")
```

Non-numeric fields and fields without a `Unit` marker pass through unchanged under `to="pint"`.
Install with `pip install dough[pint]`.
See [the units design page](design/units.md) for the full contract.

## 🧪 Testing

`dough.testing` ships shared pytest fixtures (`json_serializer`, `robust_data_regression_check`) used by downstream wrapper packages for regression tests.
It's an opt-in plugin — activate it in your top-level `conftest.py` with `pytest_plugins = ["dough.testing.plugin"]`.
See the [testing design page](design/testing.md).

## 🥟 Packages built on `dough`

| Package | Code | Status |
| --- | --- | --- |
| [`qe-tools`](https://github.com/aiidateam/qe-tools) | [Quantum ESPRESSO](https://www.quantum-espresso.org/) | alpha — `pw.x`, `dos.x` outputs |
| [`strudel`](https://github.com/mbercx/strudel) | [VASP](https://www.vasp.at/) | alpha — basic outputs + magnetization |
