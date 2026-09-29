# Changelog

## 0.3.0 — 2026-09-29

- Use Grounded-SAM-2 + Qwen-Image-2.1 as the single editing pipeline.
- Remove BrushEdit/BrushNetX runtime, dependencies, model downloads and comparison UI.
- Install the complete Qwen stack by default; retain lightweight UI/detection profiles.
- Provide an English-only README and detailed English setup and usage guide.

## 0.2.0 — 2026-09-29

- Prepared a source-only GitHub release with MIT licensing for project-authored code, concise README, collaborator setup guide and optional Google Drive model-bundle tutorial.
- Moved portable installation inputs into `requirements/`; pinned audited upstream repositories and model revisions.
- Added selective backend/UI-only installation, optional-worker smoke checks, missing-model-file recovery, release auditing, ZIP64 model bundles with SHA256, and CPU CI.
- Kept weights, virtual environments, upstream checkouts, photos, run outputs and local verification records out of Git.

## 0.1.4 — 2026-09-27

- Audited the reported building/tower run: the selected building mask was correct; the Qwen prompt discarded the user's crystal material and the model edited only the salient tower.
- Preserve the original request in every Qwen prompt mode. Default the editing UI to user-concept mode, which uses the user's request without injecting conflicting template materials or geometry.
- Bind the prompt to the complete selected object, record its index/label/bounds/pixel count/mask hash, display the active target, and clear old results when changing candidates.
- Use the original photograph as Qwen's default conditioning input. Reference masks and colored annotations produced visible contamination in visual QA; the selected mask still controls strict final compositing. Keep the explicitly configured separate-mask path with correct image-reference tags.
- Honor the requested preview size for small photos and use 40 Qwen steps. Save the actual worker conditioning prompt for inspection.

## 0.1.3 — 2026-09-27

- Added broad candidate discovery with separate related-name queries, configurable confidence floor, up to 100 candidates, and optional conservative deduplication that preserves nested whole/part alternatives.
- Added clickable mask thumbnails and search counts to both detection screens. Multiple candidates require explicit selection.
- Added Chinese building/facade/tower grounding names and batched SAM mask generation to bound GPU memory.
- Verified seven distinct candidate regions on the reported building photo; 48 orchestrator tests pass.

## 0.1.2 — 2026-09-27

- Fixed Qwen generation failing on small photos when the vision processor's minimum-pixel resize disagreed with the VAE grid. The pipeline now owns reference-image resizing for both encoders.
- Added processor regressions that reproduce the reported 696-vs-832 token mismatch and verify aligned grids across nine image-size/resolution combinations, including the reduced-resolution retry.
- The fix is applied when each Qwen worker loads; installed packages and model weights remain unchanged.

## 0.1.1 — 2026-09-27

- Localized all seven UI tabs, controls, concept cards, progress and common errors into Chinese.
- Added Chinese upload/loading/download labels through Gradio i18n; preserved schema keys and raw prompts.
- Added offline Chinese target vocabulary for grounding and consistent category constraints, while retaining English inputs.
- Added bilingual inference and prompt-preservation regressions; 44 tests pass.

## 0.1.0 — 2026-09-27

- Created isolated orchestrator, Grounded-SAM, native BrushEdit and Qwen 2.1 environments on Windows RTX 4070.
- Verified real DINO/SAM masks and actual image edits through both generators.
- Added a seven-tab local Gradio workbench, twenty design templates, editable structured concepts and backend-specific prompt compilation.
- Added worker JSON IPC, cross-process GPU locking, OOM handling, source/mask validation, metadata and exact exterior pixel compositing.
- Visual QA found unmasked drink contents returning during strict compositing. Added configurable enclosed-interior filling with protected-occluder precedence.
- Added 50 COCO photographs with provenance, optional CLIP similarity diagnostics, human ratings, benchmarks and automated checks.
