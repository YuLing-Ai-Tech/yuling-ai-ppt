# Repository instructions

- This repository is the public Python/HTML PPT engine. Keep product UI,
  accounts, cloud credentials and customer content outside it.
- Preserve controlled manifests, HTML escaping, local-only assets and visual
  QA. Do not accept arbitrary executable HTML, CSS, JavaScript or remote URLs
  from model output.
- Use Python 3.12 through `uv`; run `./tools/ci.sh --fast` before every PR and
  the complete documented suite for a release candidate.
- Do not replace visual baselines only to make a test pass. Include rendered
  evidence and explain intentional visual changes.
- Work from an approved Issue on `issue/<number>-<slug>` and merge only through
  an owner-approved pull request. Never push directly to `main`.
