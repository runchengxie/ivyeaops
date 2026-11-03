# Compact store workbench implementation plan

> Execute inline with superpowers:executing-plans. Use test-driven-development for behavioral changes and independent whole-branch review before completion.

**Goal:** One everyday screen for eMAG store evidence, prioritized adjustments and a permanent right-hand Agent conversation.
**Architecture:** Add /workbench as the landing page with compact MainLayout styling. Keep it alive during detail navigation. Reuse existing authenticated evidence API, embedded Console and permission-filtered tools. Pure helpers produce bounded suggestions and explicit store/snapshot context.
**Tech stack:** React 18, TypeScript, Vite 6, existing Node tests and Python Playwright harness.
**Spec:** docs/superpowers/specs/2026-11-04-simple-store-workbench-design.md (approved in conversation).

## Global constraints
- Preserve detail routes, backend access rules, model configuration and data. No new dependencies or platform writes.
- Unknown metrics stay unknown; evidence is labelled with snapshot and capture time.
- No model call until the user sends. Suggestions prefill only. Never mix conversations between stores silently.
- Desktop fits 1366x768; mobile tabs preserve the mounted conversation. Zoom uses accessible scrolling.

## Review focus
- Slow/out-of-order store requests must not show the previous store's evidence.
- Existing busy conversation stays bound to its original store; new/history switching is disabled while running.
- User scope is applied on both primary Agent and fallback chat paths.
- Empty/error/unauthorized and malformed count fields remain truthful and useful.
- Hidden mobile tabs and detail navigation must preserve live session state and working stop control.

### Task 1: Evidence/suggestion helpers and workbench frame
**Files:** new simpleWorkbenchData.mjs, SimpleWorkbench.tsx, simple-workbench.css; App.tsx, navRegistry.ts, MainLayout.tsx.
**Interfaces:** workbenchSuggestions(data) returns at most five evidence-based product recommendations; workbenchContext(data) returns bounded explicit store/snapshot text; suggestionPrompt(data,item) produces a user-editable question.
- [x] Write/run failing Node tests for priority order, unknown/invalid values, bounded results and prompt store/product identity.
- [x] Implement helpers and compact view using current GET /emag/stores and /emag/stores/{id}/workspace.
- [x] Register keep-alive /workbench default landing, compact shell and reachable permission-filtered More/settings/logout controls.
- [x] Run helper tests and typecheck.

### Task 2: Reuse scoped Agent conversation
**Files:** new WorkbenchChat.tsx; Console.tsx optional props; helper tests/harness fixtures.
**Interfaces:** Console receives optional contextText, promptDraft {id,text}, onBusyChange; defaults preserve all other consumers.
- [x] Test that store bindings are explicit and suggested text does not auto-send.
- [x] Implement scoped context on Agent and fallback, prompt prefill and busy notification; retain existing streaming/approval/stop behavior.
- [x] Keep conversation mounted and bound across selected store changes; per-user local history stores session references/scope, not raw snapshot data.
- [x] Run behavior and browser checks for send/stop/history/store switching/hidden tabs.

### Task 3: Verify and deliver
**Files:** scripts/verify-simple-workbench.py, harness/mockApi.ts, package.json/CI; docs usage/changelog plus Chinese usage.
- [x] Verify real App at 1366x768, 1440x900, 390x844 and zoom, including overflow/empty/error/offline states and detail navigation.
- [x] Run frontend typecheck, i18n/render/reliability/eMAG tests, error gate, audit, production build and docs link checks.
- [x] Independent whole-branch review, address important findings with red/green evidence.
- [ ] Commit/push/PR; merge after required CI, sync local main, rebuild/restart identified service if needed and safely remove merged task artifacts.

## Approved delivery addition
The user also requested publication of the new interface to the existing GitHub Pages demo. Share the workbench presentation, inject a labelled synthetic chat, keep the network-denying CSP, verify the built demo and publish through the repository Pages workflow after merge.

## Review and verification record

- Five helper tests and six synthetic-demo tests passed, with new behavior first failing before implementation.
- Primary backend/source-contract suite: 948 passed, 1 skipped. Frontend types, locale/render/reliability/eMAG tests, error-text gate, production/demo builds, Ruff and doc links passed. npm audit: zero vulnerabilities.
- Real App browser verified 1366x768, 1440x900 and 390x844: computed viewport fit, scoped prefill/send/stop, store switching, detail return, empty/error and fallback scope. Zoom retains scrollable suggestions and composer controls.
- Built demo browser verified synthetic replies/history/detail return/mobile/reset and zero backend requests.
- Independent review found two Important transitions: old attachments surviving new conversation and old session surviving failed history. Both were reproduced RED, fixed via isolated Console runtime and verified GREEN. A further generic pending-queue regression was reproduced RED and fixed with store/user queue scope. No deferred review findings.
- Ruling: keep /dashboard and other detailed routes while making /workbench the default. Ruling: share presentation with an injected synthetic demo chat so the public build does not include a live Agent client.
- Hosted CI, merge and Pages deployment are verified in the PR before final delivery.
