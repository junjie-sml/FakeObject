# Engineering notes

## Provenance and compatibility decisions

The actual official repositories were cloned and inspected. Native BrushEdit's `app/src/brushedit_all_in_one_pipeline.py` accepts a loaded pipeline, target caption, mask, original RGB array and generator. Its UI template eagerly loads multiple base models; the adapter deliberately loads only RealisticVision and BrushNetX. The native inference function is called without modification. Native VLM intent reasoning is replaced by a disclosed local deterministic target/spec stage to avoid mandatory API calls or a 7B helper.

Grounded-SAM-2's `grounded_sam2_hf_model_demo.py` documents the HF AutoProcessor / AutoModelForZeroShotObjectDetection route. The adapter examines the installed processor's signature because Transformers 4.48 uses `box_threshold` while the current example uses `threshold`. DINO is unloaded before SAM loads. SAM 2.1 tiny is selected to leave room for the OS and other work.

Qwen-Image-2.1's official README and the installed Diffusers source confirm `QwenImage21Pipeline` and up to ten image references. Its current call signature has no native `mask_image`. The default adapter supplies the source photograph plus concise selected-object instructions; final compositing enforces the selected mask. Separate-mask references remain configurable with `<image1>` / `<image2>` tags but are not the default: visual tests found mask colors leaking into generated buildings. `output_resolution` is set with width/height, and the processor's second resize is disabled to keep VAE/vision token grids aligned. Small photographs are enlarged to the requested inference size (multiples of 32).

Qwen optional native negative conditioning requires BOTH `true_cfg_scale > 1` and `negative_prompt`. The tested default remains 1, using natural-language negative constraints. Changing this config is experimental and may increase time/memory. No quantization, replacement generator or opaque third-party model is used.

## Invariants

- A worker request holds `data/cache/gpu.lock` across process startup, inference and exit. The process does not retain a model after the request.
- Request/response JSON lives in project-local IPC storage. Model stdout/stderr cannot corrupt the protocol because it goes to a separate log file.
- Workers use local files only and offline HF/Transformers flags.
- Candidates are filtered by the configured score threshold, optional deduplication and maximum count; search metadata records truncation. More than one candidate requires an explicit instance.
- Cached detection is bound to a hash of decoded pixels, image dimensions and the target phrase.
- Mask processing removes small disconnected components, fills selected enclosed interiors, supports dilation/erosion and creates inward feathering. Protected occluder pixels are applied AFTER morphology.
- Alpha is exactly zero outside the processed edit support. Composite arithmetic rounds to uint8; original pixels outside the support remain bit-exact.
- Every editing attempt writes a metadata file, including failed attempts. Failed outputs are not replaced by fabricated success images.
- Prompt scores are heuristics. CLIP scores are an explicitly named single-model diagnostic. Neither implies an ontological nonexistence claim.

## Deliberate limitations

Current scene analysis is a geometric/conservative fallback, not a semantic VLM. Automatic occluder discovery and reflection support masks are not implemented. Source leakage is represented by CLIP source-category similarity and manual review rather than a false certainty. The history page stores manual ratings.

The isolated environments and exact installs are recorded in `data/metadata/environment_versions.json`; repository/model revisions are recorded separately. Native Windows was validated; Linux/WSL scripts are supplied but have not been executed on this host (WSL is not installed).
