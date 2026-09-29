# Release validation — 2026-09-29

## Reproducible source installation

A clean source snapshot was exported without models, data, upstream checkouts
or virtual environments. On Windows / Python 3.11.7:

- `python scripts/bootstrap.py --ui-only`: succeeded, including pip dependency checks.
- CPU regression suite in the newly created environment: **69 passed, 3 skipped**.
- Fresh UI launched on a temporary test port and returned **HTTP 200**; the test service was then stopped.
- No downloaded photo dataset was needed for this validation.
- Original workspace environments (UI, detection, BrushEdit, Qwen): all four `pip check` runs passed.
- Audited dependency checkouts match `configs/repositories.json`.

The three skipped cases require the separate Qwen environment and local model
processor. CPU tests include mask selection, prompt preservation, worker failure
handling, download receipt recovery and offline bundle checksums.

## Scope of the evidence

This release validation did **not** reinstall tens of gigabytes of GPU dependencies
or rerun generation on a second machine. Existing Windows GPU inference evidence
uses RTX 4070 12 GB, 32 GB RAM. Linux/WSL2 GPU inference, other GPU architectures,
and higher-resolution profiles remain unverified. GitHub Actions tests CPU
behavior only; check the actual run status in the repository's Actions tab.

The known whole-building edit test uses the selected building mask, but Qwen
can transform the central facade more strongly than the side walls. This is a
model adherence limitation, not proof of a candidate-index error.

Local photographs, run metadata and screenshots are excluded from this source
release. Reproduce GPU checks with your own shareable photo or the optional
COCO download; see [the installation guide](INSTALLATION.zh-CN.md).
