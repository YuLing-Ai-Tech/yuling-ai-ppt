# YuLing AI PPT Engine

Open-source Python/HTML presentation engine for YuLing AI. It assembles controlled
slide fragments, styles, charts, motion and runtime assets into a single-file
HTML presentation and provides visual-quality checks for the engine surface.

## Boundary

- This repository owns the reusable HTML runtime, components, styles, builder
  and engine QA.
- The `mini-app` repository owns the user-facing Next.js product, structured
  generation, storage and orchestration.
- The current integration is intentionally file based: `mini-app` writes a
  controlled deck directory and invokes `tools/build_deck.py` through
  `PPT_ENGINE_ROOT`.

## Requirements

For the Issue #1 candidate pair, native Mac setup and remaining acceptance gates,
see [MAC_ACCEPTANCE.md](MAC_ACCEPTANCE.md) and
[BASELINE_REPRODUCTION.md](BASELINE_REPRODUCTION.md).

- Python 3.12
- `uv` 0.13.4
- Chrome or Chromium for browser-based smoke tests

Visual QA uses the system Chrome by default. To pin an isolated browser binary
without replacing the user's Chrome, set `PPT_CHROME_PATH` to its executable:

```bash
PPT_CHROME_PATH=/path/to/chrome ./tools/ci.sh
```

## Build a deck

```bash
python3 tools/build_deck.py --deck examples/图元样板 --engine-root . --out build/sample.html
```

## Tests

Fast, non-browser checks:

```bash
./tools/ci.sh --fast
```

Portable engine suite:

```bash
uv run --no-project --python 3.12 \
  --with playwright==1.60.0 --with pillow==13.0.0 --with pytest==9.1.1 \
  python -m pytest tests -q
```

Historical customer/course assets and the original repository history are
intentionally not part of this safe GitHub baseline. See
`BASELINE_MANIFEST.md` for provenance and exclusions.

## License and package status

The repository is licensed under Apache-2.0. Brand names and logos are not
licensed for reuse; see `TRADEMARKS.md`. This repository is source-available for
collaboration but does not currently publish a Python package.
