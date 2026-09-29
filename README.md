# FakeObject

**Replace an object in a real photograph with a fictional design, locally.**

A research workbench powered by **Grounded-SAM-2 + Qwen-Image-2.1**: detect candidates, select an instance, preview its mask, and generate an edit with reproducible run records. The UI is localized in Chinese; prompts accept **English and Chinese**.

[Installation and usage](docs/INSTALLATION.md) · [Architecture](docs/ARCHITECTURE.md) · [Validation](docs/VALIDATION.md) · [License notes](LICENSE_NOTES.md)

## Requirements

- **Python 3.11** (64-bit) and **Git** on PATH.
- NVIDIA CUDA GPU. Tested generation: **RTX 4070, 12 GB VRAM, 32 GB RAM**, Windows.
- Reserve **80 GB** for models, isolated environments and caches; outputs need additional space.
- Internet for installation. Image inference uses local weights and offline loading.

Windows generation is tested. Linux/WSL2 setup is provided, but GPU inference there remains unverified. CPU-only machines can use the UI and concept designer; macOS/AMD GPU generation is unsupported by this configuration.

## Quick start

Run these commands with Python 3.11:

```bash
git clone https://github.com/junjie-sml/FakeObject.git
cd FakeObject
python scripts/bootstrap.py
python scripts/launch_app.py
```

Open **http://127.0.0.1:7860** and keep the terminal running. Setup installs the UI, detector, segmenter and Qwen editor in separate environments. No backend selection is needed.

**Each collaborator downloads models directly from their official sources.** Pinned revisions are recorded in [configs/models.yaml](configs/models.yaml). Required weights total approximately **31.65 GiB** (detector/SAM: 0.79 GiB; Qwen: 30.86 GiB). Optional CLIP diagnostics add 0.57 GiB. No maintainer upload or Google Drive bundle is required. Weights, environments, private photos and outputs are excluded from Git.

For a lightweight installation:

```bash
python scripts/bootstrap.py --ui-only       # UI and concept designer; no weights
python scripts/bootstrap.py --backend none  # UI and detection; no image generation
```

## First edit

1. Upload your photograph and enter a short target name, such as `building` or `cup`.
2. Run detection. Click a candidate thumbnail and confirm its number and green mask.
3. Enter your request, for example: `Turn the selected building into crystal while retaining its architectural style. Modify every visible facade.`
4. Keep the default user-concept mode, preview quality and strict preservation enabled. Start generation.
5. Scroll below the prompt fields to see the raw model output and strictly composited output. Saved runs also appear in the history tab.

The [usage guide](docs/INSTALLATION.md#using-the-ui) explains the controls in English. A preview run took approximately two minutes on the tested machine, including loading. Performance varies with hardware and image size.

Strict compositing preserves original pixels wherever the final alpha mask is zero. It cannot force the model to change every pixel inside the mask. Large or occluded targets may be only partially transformed. Concept suggestions use deterministic local templates, not a semantic vision-language model.

## Validation

Windows:

```powershell
envs\orchestrator\Scripts\python.exe -m pytest -q
envs\orchestrator\Scripts\python.exe scripts/run_smoke_tests.py
```

Linux/WSL2: use `envs/orchestrator/bin/python` instead. CPU tests need no GPU weights; Qwen processor tests skip when their dependencies are absent. See [validation evidence](docs/VALIDATION.md) and [troubleshooting](docs/INSTALLATION.md#troubleshooting).

## Project layout

```text
src/              UI, orchestration, workers, prompts, compositing, evaluation
configs/          Runtime settings and pinned model/repository revisions
requirements/     Environment inputs and tested package constraints
scripts/          Setup, download, validation and demo tools
tests/            CPU regressions and optional Qwen processor checks
data/outputs/     Local images, masks, prompts and metadata (not committed)
```

GPU jobs are serialized and run in isolated processes that exit after each request. Keep the UI, detection and Qwen environments separate.

## License

Project-authored code is **[MIT](LICENSE)**. Upstream code, model weights and photographs retain their own terms. The project license does not relicense Qwen weights; review [LICENSE_NOTES.md](LICENSE_NOTES.md) before use or redistribution.
