---
name: fake-object-design
description: Design physically plausible, category-ambiguous fictional replacement objects for real photographs, using structured specifications and backend-specific prompts. Use for object replacement concept development in this project, not general image stylization.
---

Create a `FakeObjectSpec` using `src/prompting/schemas.py`. Generate three concepts with `generate_concepts` before expensive image inference. Select from the twenty inspiration templates in [templates.yaml](templates.yaml); vary geometry, compatible materials and muted colors while keeping target and scene constraints fixed across seeds.

Use one primary geometry and one major secondary structure, with one or two minor manufactured details. Keep 1–3 coherent materials, gravity, stable support, roughly the source footprint, camera perspective, lighting, contact shadow, focus and grain. Do not assume unknown scene attributes; label fallback constraints. For handheld objects preserve finger occlusion; for transparent objects reconstruct the old transmitted background.

Reject category swaps and familiar products with cosmetic changes when the user requests fictional objects. Avoid fantasy, neon, unexplained levitation and obvious sci-fi styling unless requested. Semantic unfamiliarity is a research criterion, not proof that an object does not exist.

Preserve a detailed user concept in minimal-polish mode. Do not let templates overwrite it. Use `prompt_validator.py` for explicitly heuristic text scores. These are not image-quality measurements. Keep user design intent, target, scene, exclusions and physical constraints in separate schema fields.

Compile Qwen as an editing instruction with preservation language. Never replace one image model with another silently. Keep raw and strict-composited outputs and record the full spec, seed and backend prompt. Examples: [examples.json](examples.json).
