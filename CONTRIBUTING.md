# Collaboration workflow

The public baseline root commit is the only direct push to `main`.

1. Claim an approved GitHub Issue.
2. Create `issue/<number>-<short-slug>` from the current `main`.
3. Keep changes within the Issue scope and include test evidence.
4. Open a pull request and wait for the repository owner's approval.
5. Do not push directly to `main`, rewrite history, upload credentials, or
   replace visual baselines only to make a check pass.

The `main` ruleset enforces the pull-request, review and CI gates. Contributions
submitted for inclusion are licensed under Apache-2.0 unless explicitly marked
otherwise before submission.
