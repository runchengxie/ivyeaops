# eMAG evidence playbooks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver source-linked local eMAG workflows for existing-stock repair, Listing, variants, competitor observations, advertising, inbound checks and cost evidence.

**Architecture:** Pure validated assessment rules feed a snapshot-bound private ledger and admin API. A bilingual React panel uses the existing App and workspace routes. No marketplace writer is introduced.

**Tech Stack:** Existing FastAPI, Pydantic, SQLite, React, TypeScript, Vite; no new runtime dependency.

**Spec:** `docs/superpowers/specs/2026-11-07-emag-evidence-playbooks.md`

## Global Constraints

- All records stay private under configured data_dir; no original private files committed.
- Default English and persisted explicit Chinese switch for new UI, catalogs not inline product copy.
- Authentication, immutable snapshots, optimistic revisions and no marketplace execution.
- Unknown is distinct from zero; manual evidence is not platform verification.

## Review Focus

- A record referencing a different store's product cannot enter this ledger.
- Historical assessments must never appear as current after snapshot changes.
- Blank/zero advertising metrics and mismatched periods cannot imply profitability.
- Untrusted links and remote text must never execute or render raw HTML.
- Duplicate variant members and contradictory inbound barcodes cannot look ready.

### Task 1: Deterministic rules and source registry

Files: create `src/server/app/services/emag_playbook_rules.py`, tests `src/server/app/tests/test_emag_playbook_rules.py`.
Interfaces: `sources()`, `repair_guidance(snapshot)`, `validate_payload(kind,payload,offers)`, `assess(kind,payload,offers)` per spec.
- [ ] Write failing boundary and readiness tests, run them RED.
- [ ] Implement validated seven-kind payloads, assessments and reference metadata.
- [ ] Run rule tests GREEN and backend lint.

### Task 2: Private ledger and admin API

Files: create `src/server/app/services/emag_playbooks.py`, extend `src/server/app/routers/emag_operations.py`, tests `src/server/app/tests/test_emag_playbooks.py`.
Consumes Task 1 interfaces. Produces GET workspace and POST revision-checked records per spec.
- [ ] Write failing API/auth/staleness/store/revision tests and run RED.
- [ ] Implement atomic persistence, historical assessment handling and router.
- [ ] Run new tests plus existing workspace/commerce/operations regressions.

### Task 3: Bilingual workspace panel

Files: create focused `src/client/src/pages/workbench/playbooks/` panel/types/catalogs; modify `EmagWorkspace.tsx`; real App harness fixtures and regression checks.
Consumes Task 2 API contract. No shared files with rule/store implementers.
- [ ] Add failing locale/data contract tests and real harness scenarios.
- [ ] Implement seven forms, product/store guards, edit revisions, errors, histories, source-linked repair guidance, contextual source metadata and checks.
- [ ] Run client typecheck, i18n, build and real App harness UI validation.

### Task 4: Documentation, review and integration

Files: maintained English and Chinese usage docs, indexed ADR, changelog.
- [ ] Document actual workflows and limitations, private archive mapping and no execution.
- [ ] Run required full checks, independent whole-branch review and fix material findings.
- [ ] Verify GitHub owner/push destination, PR checks on current base, merge, verify merged checks/site and clean only task branch/worktree.
