# Contributing

Use Python 3.11 and start with `python scripts/bootstrap.py --ui-only`.
On Windows run `envs\orchestrator\Scripts\python.exe -m pytest -q`;
on Linux use `envs/orchestrator/bin/python -m pytest -q`.

- Keep GPU libraries out of the UI process. Add worker-specific dependencies to `requirements/`.
- Pin upstream revisions in `configs/repositories.json` / `configs/models.yaml`.
- Include a focused regression for behavioral changes. Report GPU, resolution,
  backend and actual visual limitations for model changes; passing CPU tests
  is not evidence that generation quality improved.
- Do not commit photographs, outputs, environments, caches, model weights or tokens.
- Before pushing, stage changes and run `scripts/check_release.py` with the UI environment.
- Preserve third-party attribution and licensing. The root MIT license covers
  project-authored code, not upstream models/photos.

Open a pull request with the problem, resulting behavior and validation performed.
Bug reports should include the backend, OS/GPU, Python version and a sanitized
error excerpt. Use a shareable test image rather than a private photograph.
