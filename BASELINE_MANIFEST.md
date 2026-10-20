# Public safe baseline manifest

- Public baseline date: 2026-10-20
- Source provenance: reviewed safe snapshot of the former private engine and
  visual-QA candidate; prior commit identifiers remain only in the local audit
  archive.
- Intended tag: `public-baseline-2026-10-20`

## Included candidate changes

- Controlled commercial and research chart rendering
- Semantic motion runtime and Apple-style motion assets
- Navigation and visual-QA fixes required by the PPT application
- Portable test dependencies and synthetic chart/motion fixtures

## Deliberate exclusions

- Original Git history
- Historical 94-page course deck, personal QR/contact assets and third-party
  product screenshots
- Draft plans, handoff notes, prototypes and unreviewed archives
- Build output, caches, generated screenshots and machine-local files
- Historical regression tests whose only fixture was the excluded 94-page deck
- Private GitHub Issues, pull requests, Actions logs and deployment traces

`tests/test_build.py` uses a synthetic local fixture so core builder behavior
remains covered without the excluded historical material.

## Pre-bootstrap evidence

- Mini-App with the old base engine: 39/43 tests passed; four browser QA tests
  failed.
- Mini-App with the visual-qa candidate: 43/43 tests passed.
- Candidate portable engine suite, excluding the two historical-asset test
  files before snapshot cleanup: 161 passed in 574.34 seconds using Python
  3.12, pytest 9.1.1, Playwright 1.60.0 and Pillow 12.3.0.

The committed snapshot must be retested independently; this document records
source provenance rather than claiming future runs have passed.

## Safe snapshot verification

- Public-candidate fast gate: 55 passed, 111 deselected in 3.29 seconds.
- Public-candidate complete portable suite: 166 passed in 580.54 seconds.
- Gitleaks directory scan: no leaks found in the staged snapshot.
- Visual sample inspection: baseline pages 1, 5 and 9 reviewed; no customer
  material, personal contact details or QR codes found.
