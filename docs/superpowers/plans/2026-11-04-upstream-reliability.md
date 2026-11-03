# Upstream reliability implementation plan

> Execute inline with superpowers:executing-plans; verify each behavioral regression before completion.

**Goal:** Port the four general reliability fixes from upstream ef6a5ae without cockpit redesign or eMAG business changes.
**Architecture:** Adapt upstream patches to src/client and src/server. Preserve existing error contracts outside /api/agents and existing download names.
**Tech Stack:** React 18, TypeScript, FastAPI, Python 3.12, Node 26.
**Spec:** User-approved approach in the conversation: selectively port general fixes, assess visual redesign separately.

## Global constraints
- No dependencies, submodule updates, credentials or user data changes.
- English new source comments and user-facing changelog; maintain Chinese changelog translation.
- Preserve the real App tree in harness validation.

## Review focus
- 401/403 rejects immediately; network/5xx recovers without login navigation.
- Cancelled auth checks never update unmounted components.
- Plugin errors including validation arrays remain renderable strings.
- Download cleanup preserves filenames and defers object URL revocation.
- Disabled version checks make no health or GitHub requests.

### Task 1: Auth and Agent compatibility
- [x] Add behavioral regression tests for auth retries/cancellation and plugin error envelopes; observe failures.
- [x] Adapt auth guard, plugin error formatting/backend stub, disable irrelevant version polling.
- [x] Run regression tests and frontend typecheck.

### Task 2: Download lifecycle
- [x] Add behavior tests asserting anchor attachment, names, cleanup and delayed revocation; observe failure.
- [x] Port saveBlob/saveText utility and migrate existing immediate-revocation download consumers.
- [x] Run regression tests, locale contracts and build.

### Task 3: Integration and delivery
- [x] Update changelogs and record upstream provenance.
- [ ] Run backend lint/tests, frontend checks, dependency audit and real App harness browser verification.
- [ ] Review whole branch, resolve material findings, push PR and merge when checks pass.
- [ ] Sync main, restart specifically identified local service and verify health; clean only this task's safe temporary branch/worktree.

## Execution evidence

- Frontend: 5 new behavior tests passed; baseline plugin-string/polling cases failed on original main. Typecheck, 8 locale tests, 2 render tests, error-text gate and production/demo builds passed; npm audit reported zero vulnerabilities.
- Backend: 947 passed, 1 skipped in primary suite; 12 compatibility/error-contract tests passed; Ruff and maintained doc links passed.
- Browser: real App harness in isolated Edge passed transient failure, offline/recovery, 403 and actual report download; computed offline title is 16px.
- Independent review: no Critical/Important findings. Deferred minor: provider-level malformed/null/invalid JSON coverage; current helper envelope coverage and adapter inspection passed.
- Ruling: keep the outage fixture failed until explicitly restored, because StrictMode repeats initial checks; no product behavior change.
- App suite and hosted CI are pending at initial commit; results recorded in the PR before merge.
