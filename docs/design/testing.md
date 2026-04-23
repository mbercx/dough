# Testing

`dough.testing` ships shared pytest fixtures for downstream `dough`-based packages.

!!! note "Scope"

    `dough.testing` provides cross-package test helpers only.
    It does not ship test data, assertions, or anything beyond regression-snapshotting fixtures.

## Fixtures

Two fixtures are exposed via `dough.testing.plugin`.
Both accept `(data, max_number=None)`.
Pass `max_number=N` when the regression snapshot would otherwise be huge — the fixture thins lists/arrays down to `N` equally spaced elements before the diff.

### `json_serializer`

Factory that makes arbitrary data JSON-serializable for regression snapshots.
Rounds floats to 5 digits, coerces `numpy.ndarray` via `.tolist()` (complex arrays split into `[real, imag]` pairs), and optionally subsamples lists/arrays to `max_number` equally spaced elements.
Raises `TypeError` on unsupported types.

### `robust_data_regression_check`

Wraps `pytest-regressions`' `data_regression.check`, piping the data through `json_serializer` first.
Accepts the same `max_number` kwarg for subsampling.

## Registration

The plugin is **opt-in**.
Downstream packages activate it by adding one line to their top-level `conftest.py`:

```python
pytest_plugins = ["dough.testing.plugin"]
```

This is intentional.
Registering `dough.testing.plugin` as a `pytest11` entry point would auto-load the fixtures in any environment that happens to have `dough` installed — even environments that use `dough` only as a runtime dependency and never call into the testing layer.
Explicit registration keeps the "where do these fixtures come from?" trail one `grep` away, and avoids injecting pytest fixtures into unrelated test suites.

## Dependency policy

`dough` itself declares `pytest-regressions` and `numpy` under the `[tests]` extra.
`numpy` is imported lazily inside `dough.testing._serialize` so that `dough`'s runtime surface stays numpy-free — the fixture still works on pure-Python data without `numpy` installed, mirroring the lazy-import rule already used for `ase`/`pymatgen`/`aiida-core` in the converters.
