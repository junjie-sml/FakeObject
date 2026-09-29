# FakeObject

**Replace an object in a real photograph with a fictional design — locally.**

A Chinese-language research UI with Chinese/English prompts, selectable detection candidates, mask previews, two image-editing backends, and reproducible run records.

[中文安装与操作教程](docs/INSTALLATION.zh-CN.md) · [Publishing & Google Drive guide](docs/PUBLISHING.zh-CN.md) · [Architecture](docs/ARCHITECTURE.md) · [License notes](LICENSE_NOTES.md)

## What it does

1. Upload a photograph and describe the target.
2. Detect candidates with Grounding DINO + SAM 2.1; select the exact instance.
3. Enter your own edit request or explore three fictional-object concepts.
4. Generate with **BrushEdit / BrushNetX** or **Qwen-Image-2.1**.
5. Compare the raw edit with the strictly composited result; download images and metadata.

Strict compositing preserves pixels where the final alpha mask is zero. It does **not** guarantee that the generator changes every part inside the mask. Concepts use local deterministic templates, not a semantic VLM.

## Requirements

| Component | Supported baseline |
|---|---|
| Python | **3.11**, 64-bit; Git on PATH |
| GPU generation | NVIDIA CUDA GPU; tested on RTX 4070 **12 GB VRAM**, **32 GB RAM** |
| System | Windows tested; Linux/WSL2 installation path provided, GPU inference not yet validated there |
| Disk | Reserve **100 GB** for both backends, environments and caches |
| Network | Required for installation; image workers use offline local model loading |

CPU-only machines can run the UI and prompt designer (`--ui-only`), but cannot run the CUDA generation workers. macOS/AMD GPU generation and newer GPU architectures requiring different CUDA wheels are not supported by the tested configuration.

## Quick start

Use a terminal where `python --version` reports **3.11**. No activation is required after setup.

```bash
git clone https://github.com/junjie-sml/FakeObject.git
cd FakeObject
python scripts/bootstrap.py --backend qwen
python scripts/launch_app.py
```

Open **http://127.0.0.1:7860** and keep the terminal running. Select **B · Grounded-SAM-2 + Qwen 2.1** for the Qwen-only installation; the UI initially selects backend A. Upload your own photo; demo images are optional.

Choose a different installation profile:

```bash
python scripts/bootstrap.py --backend brushedit  # Detector + BrushEdit
python scripts/bootstrap.py --full               # Both editors + detector
python scripts/bootstrap.py                     # Detector only; no image generation
python scripts/bootstrap.py --ui-only            # UI/designer only; no model downloads
```

Model downloads: detector/SAM **0.79 GiB**, BrushEdit **7.41 GiB**, Qwen **30.86 GiB**; optional CLIP **0.57 GiB**. Models are fetched from official repositories at revisions recorded in [`configs/models.yaml`](configs/models.yaml). Model weights, virtual environments, photographs and outputs are **not** in Git.

## First edit

- Upload a photo. Enter target `建筑` / `building`, or another short object name.
- Click **检测目标**, then click a candidate thumbnail. Confirm **当前编辑目标** and the green mask.
- Keep **沿用用户构想** to follow your request. Example: `把选中的建筑改成水晶材质，保持原有风格。`
- Choose an installed backend and **预览（已验证）**, then click **开始生成**.
- Scroll to **模型原始生成结果** and **严格保持场景的结果** below the prompt fields. Saved runs are also in **结果与历史**.

Qwen accepts Chinese/English design details. BrushEdit uses an English text encoder; English prompts/target descriptions are preferable. Start with preview resolution: a Qwen run took approximately **2 minutes** on the tested machine; speed varies with CPU/RAM/offload and image size.

## Validate

Windows:

```powershell
envs\orchestrator\Scripts\python.exe -m pytest -q
envs\orchestrator\Scripts\python.exe scripts/run_smoke_tests.py
```

Linux/WSL2: replace `envs\orchestrator\Scripts\python.exe` with `envs/orchestrator/bin/python`. Tests do not require downloading GPU weights. Optional environments are skipped when absent. [Full validation and troubleshooting](docs/INSTALLATION.zh-CN.md#验证与排错).

## Layout

```text
src/              UI, orchestration, workers, prompts, compositing, evaluation
configs/          Runtime configuration + pinned model/repository revisions
requirements/     Environment inputs + tested package constraints
scripts/          Setup, downloads, validation, demos, publishing checks
skills/           Local design templates and examples
tests/            CPU tests and optional Qwen processor regressions
data/outputs/     Generated locally: images, prompts, masks and metadata
```

Each GPU job runs in an isolated process and exits to release its models. BrushEdit, detection and Qwen use separate environments to avoid conflicting Torch/Diffusers versions. Do not merge them into one environment.

## Limits & license

Preview generation has been exercised on Windows; higher resolutions are experimental. Large/occluded targets can be only partially transformed. Strict compositing may preserve an unwanted reflection or shadow outside the selected region. No automatic realism or novelty guarantee is made.

Project-authored code: **[MIT](LICENSE)**. Upstream code, weights and photographs retain their own terms; MIT does not relicense them. Qwen and BrushEdit have important model-use restrictions: read [LICENSE_NOTES.md](LICENSE_NOTES.md) before use or redistribution.
