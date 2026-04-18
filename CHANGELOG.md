# Changelog

## v0.2.0

### 💥 Breaking changes

* `output_mapping`: Move `Spec` into `Annotated[T, Spec(...)]` [[dc7dc58](https://github.com/mbercx/dough/commit/dc7dc58382e9183d0d44db37c78d7a020d197873)]

### 📚 Documentation

* `docs`: Add design doc for output machinery [[8f1b6f7](https://github.com/mbercx/dough/commit/8f1b6f7205135cd88c94eab39267312ba750c98f)]

### Developer

#### 🧪 Tests

* `tests`: Expand coverage for base outputs, converters, and parsers [[d56772b](https://github.com/mbercx/dough/commit/d56772b00444faf5013b670d882f11f7795dec50)]
* `tests`: Replace placeholder test with `__about__` coverage [[6cdcba8](https://github.com/mbercx/dough/commit/6cdcba83c6406eb7617c86b5843bd4a762f8f9dd)]

#### 🔧 DevOps

* `mypy`: Ignore missing imports for `glom` via override [[9f0e4b8](https://github.com/mbercx/dough/commit/9f0e4b8218666817d4b8d4395b5d2f36f9f925d0)]

## v0.1.0

First release, mostly to reserve the name on PyPI.
Still pretty raw though.

### ✨ New features

* `dough`: Expose public API for base machinery [[7af732c](https://github.com/mbercx/dough/commit/7af732c0fdff6d3a2ca668a5c686a2d7eb01e2cf)]
* `dough`: move in generic base I/O layer from `qe-tools` [[7e217df](https://github.com/mbercx/dough/commit/7e217dfac8edec8fdbfbbc6c66bbc3956e75cc2b)]

### Developer

#### 🔧 DevOps

* `copier`: update package template to v0.14.1 [[898aeae](https://github.com/mbercx/dough/commit/898aeaeab891e6c93923b5b64bfbc02e53a8108b)]
* `.gitignore`: Add `local/` to ignored paths [[f17b300](https://github.com/mbercx/dough/commit/f17b3007245d7abce4051cce51b05caeff40af67)]
