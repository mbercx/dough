"""Pure serialization helpers for regression-test fixtures.

Kept separate from `plugin.py` so the helpers are unit-testable without
going through pytest's fixture machinery. `numpy` is imported lazily so
`dough` has no numpy runtime dependency.
"""

from __future__ import annotations

from typing import Any


def _get_equally_spaced(array: Any, max_number: int) -> Any:
    """Return `max_number` equally spaced elements from `array`."""
    if max_number <= 1:
        return [array[0]] if len(array) else []

    indices: Any
    try:
        import numpy as np

        indices = np.linspace(0, len(array) - 1, max_number, dtype=int)
    except ImportError:  # pragma: no cover
        step = (len(array) - 1) / (max_number - 1)
        indices = [round(i * step) for i in range(max_number)]

    if isinstance(array, (list, tuple)):
        return [array[i] for i in indices]
    return array[indices]


def _serialize(item: Any, max_number: int | None = None) -> Any:
    """Recursively make `item` JSON-serializable for regression tests.

    - `str`, `bool`: returned as-is.
    - `float`, `int`: converted to `float` rounded to 5 digits.
    - `list`, `tuple`: recursed; subsampled to `max_number` when set.
    - `numpy.ndarray`: complex arrays split into `[real, imag]` lists;
      others converted via `.tolist()`. Subsampled when `max_number` is set.
    - `dict`: recursed on values.
    - Anything else: `TypeError`.
    """
    if isinstance(item, (str, bool)):
        return item
    if isinstance(item, dict):
        return {k: _serialize(v, max_number) for k, v in item.items()}
    if isinstance(item, (list, tuple)):
        serialized = [_serialize(el, max_number) for el in item]
        if max_number is not None and len(serialized) > max_number:
            serialized = _get_equally_spaced(serialized, max_number)
        return serialized

    try:
        import numpy as np

        if isinstance(item, np.integer):
            return round(float(item), 5)
        if isinstance(item, np.floating):
            return round(float(item), 5)
        if isinstance(item, np.ndarray):
            if np.iscomplexobj(item):
                return [
                    _serialize(item.real, max_number),
                    _serialize(item.imag, max_number),
                ]
            if max_number is not None and item.size > max_number:
                item = _get_equally_spaced(item, max_number)
            return _serialize(item.tolist(), max_number)
    except ImportError:  # pragma: no cover
        pass

    if isinstance(item, (float, int)):
        return round(float(item), 5)

    raise TypeError(f"Type '{type(item)}' not supported by _serialize")
