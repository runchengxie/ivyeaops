# eMAG Market Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Connect explicit profitability, traceable opportunities and quote history to local decisions.
**Architecture:** Extend commerce Decimal scenarios; private SQLite research ledger; bilingual real App panels.
**Tech Stack:** FastAPI, SQLite, Decimal, React/Vite.
**Spec:** ../specs/2026-11-08-emag-market-research-design.zh-CN.md (user approved)

## Global Constraints
No marketplace writes, credential replacement or invented market figures. Missing inputs stay unknown. Store source, observation time, country, currency and tax basis. Preserve auth and existing data.

## Review Focus
Zero revenue/infeasible targets; incomparable observations; historical evidence misrepresented as current; ambiguous PNK; concurrent saves and atomic import rollback.

### Task 1: Profitability
Files: services/emag_commerce.py, routers/emag_operations.py, tests/test_emag_commerce.py.
Interface: calculate(inputs,offer) adds contribution_margin_pct, break_even_ex_vat_ron, target_sale_ex_vat_ron; optional target_margin_pct. Authenticated read-only POST commerce/{product}/scenario binds snapshot and explicit sale_price.
- [ ] Test RED: revenue100, cost50, commission10%, VAT20% => contribution38, margin38%, break-even56.82, target20% price73.53; zero/missing/infeasible inputs unknown; extreme decimals rejected.
- [ ] Implement, commerce suite GREEN, commit.

### Task 2: Research ledger
Files: services/emag_research.py, routers/emag_research.py, router registration, tests/test_emag_research.py.
Interface: GET/POST /stores/{store}/research and POST /research/import; schema1 opportunity/quote records, immutable revisions, optimistic revision and snapshot binding. GET includes exact-PNK matches, comparable observations, historical changes and local prompts.
- [ ] Test RED: persistence/revisions, stale snapshot, zero/unknown, ambiguous PNK, country/currency/tax mismatch, unsafe URL, atomic import rollback and auth.
- [ ] Implement; research and adjacent tests GREEN; commit.

### Task 3: UI
Files: workbench/research component/catalogs, EmagWorkspace, EmagCommerce, harness/e2e.
Interface: task1/2 APIs, persisted English/Chinese switch, opportunity/quote/history/import and profitability scenarios.
- [ ] Executable locale/payload tests RED; implement UI/error/conflict/stale/reset states.
- [ ] Typecheck/i18n/build/regressions and real App desktop/mobile validation; commit.

### Task 4: Readiness and integration
Files: bilingual guide, source capabilities, changelog, indexed ADR.
- [ ] Inventory designated runtime/config/data; verify source access gaps and public integration contracts.
- [ ] Isolated authenticated service save/restart persistence; distinguish demo and real data.
- [ ] Backend suites in separate CI processes, ruff, client checks, docs; fresh whole-branch review/fixes.
- [ ] PR/checks/authorized merge, merged verification, cleanup only task artifacts.
