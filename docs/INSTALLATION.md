# Installation and usage

This guide starts from a clean machine. Model downloads come directly from official sources at pinned revisions; no shared Drive archive is needed.

## Prepare the machine

Install 64-bit Python **3.11** and Git, then reopen the terminal:

```bash
python --version
git --version
nvidia-smi
```

The tested GPU configuration is Windows, RTX 4070 with 12 GB VRAM and 32 GB system RAM. Reserve 80 GB for installation and additional space for results. Detection and Qwen use PyTorch 2.6.0 / CUDA 12.4 wheels. A compatible NVIDIA driver is required; a separate CUDA Toolkit is normally unnecessary. New GPU architectures requiring different wheels are not covered by this tested profile.

On Windows, use `py -3.11` if `python` selects another version. Conda users may create a Python 3.11 bootstrap environment first; the installer still creates project-local virtual environments. Do not copy `envs/` between machines.

## Install

```bash
git clone https://github.com/junjie-sml/FakeObject.git
cd FakeObject
python scripts/bootstrap.py
```

The installer creates three environments, fetches pinned upstream code and weights, and checks dependencies:

| Environment | Purpose |
|---|---|
| `orchestrator` | Gradio UI, prompts, masks and orchestration |
| `grounded_sam` | Grounding DINO detection and SAM 2.1 segmentation |
| `qwen_image` | Qwen-Image-2.1 generation |

Required model downloads total about 31.65 GiB. Dependency packages and caches are additional. Keep the terminal open and run only one installer at a time. Retry the same command after an interrupted download. Completed models with valid download receipts are reused. Existing upstream checkouts with different revisions or modifications are preserved; use a fresh project checkout if they conflict.

Optional installation profiles:

```bash
python scripts/bootstrap.py --ui-only       # No GPU environments or model downloads
python scripts/bootstrap.py --backend none  # Detection only, no generation
```

Running the default command later adds the complete generation stack. `--backend qwen` and `--full` are aliases for the default full setup.

### Linux / WSL2

Use a separate Linux checkout and Python 3.11 with venv/pip available:

```bash
python3.11 scripts/bootstrap.py
python3.11 scripts/launch_app.py
```

Do not reuse Windows virtual environments. The optional SAM CUDA extension is disabled by default. GPU inference on Linux/WSL2 has not been validated on the maintainer's machine. CPU validation is covered by GitHub Actions.

For a remote server, forward the local-only UI port:

```bash
ssh -L 7860:127.0.0.1:7860 your-user@your-server
```

### Optional data and diagnostics

Your own photos are sufficient. To populate demo images, run the following with the orchestrator Python:

```powershell
envs\orchestrator\Scripts\python.exe scripts/collect_test_images.py --count 50
envs\orchestrator\Scripts\python.exe scripts/download_models.py --model clip
```

The first command downloads a COCO annotation archive plus selected photos, recording sources and licenses locally. The second independently adds about 0.57 GiB of CLIP weights for optional similarity diagnostics. Neither is required for generation. On Linux, replace the interpreter path with `envs/orchestrator/bin/python`.

## Launch and stop

```bash
python scripts/launch_app.py
```

Open **http://127.0.0.1:7860**. The launcher selects the orchestrator environment automatically. Keep the terminal open; Ctrl+C stops the service. Restart it after rebooting.

If the port is occupied, set `FAKE_OBJECT_PORT` before launch:

```powershell
$env:FAKE_OBJECT_PORT="7861"
python scripts/launch_app.py
```

Linux: `FAKE_OBJECT_PORT=7861 python3.11 scripts/launch_app.py`. The application does not automatically read `.env`; `.env.example` is a reference.

## Using the UI

The UI labels are currently Chinese. This guide describes controls in English, in their visual order. Prompts and target names accept English and Chinese.

1. **Single-image editor (first tab):** upload a photograph at the upper left. Enter your full editing request and a short target name such as `building`.
2. **Detection settings:** broad search is the default, with a 0.15 minimum score and up to 50 candidates. Add alternative target names or lower the threshold if needed. Whole objects and their parts may both appear; detection does not guarantee every possible match.
3. **Detect target:** click the detection button, then a candidate thumbnail on the right or its entry in the instance dropdown. Confirm the selected candidate number and green mask. Multiple candidates require an explicit selection.
4. **Mask preview:** adjust dilation and feathering in advanced settings if needed. Interior holes are filled by default; disable this to preserve actual openings. White pixels in the optional foreground protection mask remain unchanged.
5. **Prompt mode:** the default follows your own concept. To explore suggested geometry, choose autonomous/exploration mode and generate three concepts, then choose A, B or C. These are design concepts for the same Qwen pipeline. Editing the target or instruction requires regenerating any stale concept JSON.
6. **Generate:** start with preview quality, seed 42 and strict preservation enabled. Click the large green generation button. A tested preview run took roughly two minutes including model loading; avoid repeated submissions.
7. **Results:** scroll below the prompt fields on the right. The left image is the raw model result; the right image is the strictly composited result. Use the download controls or the history tab. Changing candidates clears displayed results from the previous selection.

Other tabs provide a text-only concept designer, detection/mask experiments, optional dataset browsing, saved results and system status. No pipeline selector or backend comparison is required.

## Outputs and reproducibility

Runs are saved under `data/outputs/YYYY-MM-DD/RUN_ID/` using UTC dates.

| Files | Contents |
|---|---|
| `original.png`, `raw_mask.png` | Input and selected instance mask |
| `processed_mask.png`, `alpha_mask.png`, `mask_overlay.png` | Edit support, blending and preview |
| `raw_output.png`, `strict_output.png`, `final_output.png` | Generated, composited and selected final outputs |
| `prompt.txt`, `conditioning_prompt.txt` | Compiled and final Qwen prompts |
| `metadata.json`, `logs.txt` | Selection, settings, versions, timing and diagnostics/errors |

Metadata records the candidate number, label, bounds, mask pixels and hash. JSON indices start at zero; UI numbering starts at one. Identical seeds do not guarantee pixel-identical results across devices or software versions.

Strict compositing keeps pixels with alpha zero unchanged; dilation increases the editable area and feathering blends its edge. It does not guarantee full transformation within the selection, or update reflections/shadows outside it. A completed run indicates saved computation, not guaranteed visual quality.

## Validate

Windows, from the repository root:

```powershell
envs\orchestrator\Scripts\python.exe -m pytest -q
envs\orchestrator\Scripts\python.exe scripts/run_smoke_tests.py
envs\orchestrator\Scripts\python.exe scripts/verify_installation.py
```

Use `--ui-only` on the smoke command for a CPU-only installation. Missing optional workers are skipped. After downloading demo images, these commands exercise real GPU work:

```powershell
envs\orchestrator\Scripts\python.exe scripts/run_smoke_tests.py --inference
envs\orchestrator\Scripts\python.exe scripts/first_demo.py
envs\qwen_image\Scripts\python.exe -m unittest discover -s tests -p test_qwen_preprocessing.py -v
```

The inference smoke check performs detection/segmentation; the demo command generates an image and explicitly chooses the largest detection box. The interactive UI requires your selection. Processor regressions use local processor files without loading generation weights.

## Troubleshooting

| Symptom | Action |
|---|---|
| Page does not open | Check the launch terminal, wait for the URL, and verify the port is free. Restart the launcher if it exited. |
| Wrong Python version | Use `py -3.11` or `python3.11`; do not build these pinned environments with Python 3.12+. |
| Git not found | Install Git, reopen the terminal, and check `git --version`. |
| Download interrupted | Repeat bootstrap or the model download command. |
| Download returns 401/403 | Check official model access terms; set an authorized `HF_TOKEN` in the shell if required. Never commit it. |
| UI works but generation is unavailable | Run default bootstrap to install detection and Qwen, then inspect system status. |
| CUDA unavailable or out of memory | Check the worker environment, driver and GPU support. Start at preview quality and close other GPU jobs; inspect worker logs if the lower-resolution retry fails. |
| Only part of the target changes | Confirm the selected mask, simplify the request and use user-concept mode. Model adherence remains limited. |
| Stale target or prompt | Detect again or regenerate the concept rather than reusing old JSON/masks. |
| Higher resolution is unstable | Return to 512 preview; 768/1024 profiles are experimental. |

Include OS, GPU, Python version, run ID and the relevant log tail when reporting problems. Keep private images and credentials out of reports.

## Update

Stop GPU work and the UI, preserve local changes, then run:

```bash
git pull --ff-only
python scripts/bootstrap.py
python scripts/launch_app.py
```

If upstream pins changed and conflict with existing checkouts, install in a fresh project directory. Keep the pinned Torch/Transformers/Diffusers versions together. See [license notes](../LICENSE_NOTES.md) and [validation scope](VALIDATION.md).
