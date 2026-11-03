# Clearance follow-up implementation plan

> Required workflow: superpowers:executing-plans, inline; one independent whole-branch review.

Goal: reusable read-only clearance review through HTTP and MCP, and a portable price-validation runbook.
Spec: docs/superpowers/specs/2026-11-03-clearance-followup-design.md

- [ ] Test first: compatible/foreign/future baselines, missing stock/product, identity drift, changed blockers, HTTP auth and read-only MCP validation.
- [ ] Add services/emag_clearance_review.py: build(current, baseline=None), read(store_id, baseline_snapshot_id=None). Queue uses existing clearance ranking. Compare exact identity; flag exclusions; references locate both snapshots. Add no financial or sales inference.
- [ ] Expose administrator GET /api/emag/stores/{store_id}/clearance-review and read-scope ivyea_emag_clearance_review. Reject unexpected/nonstring optional arguments.
- [ ] Add plain Markdown skill for current-price validation and outcome review. Document English/Chinese API/MCP use, limitations and changelog; indexed ADR.
- [ ] Verify focused tests, full app/tests, lint, docs; independent review; fix once; CI, PR, merge and deploy under standing authorization.

Baseline: 13 focused assertions passed, but pytest session teardown failed on an existing inaccessible global temp junction. Use a task-owned --basetemp rather than modifying user temp data. No dependencies changed, so dependency baseline unchanged. Ruling: implement a read-only review and portable workflow first, not a browser-write HTTP endpoint; persistent backend browser execution needs a separate ownership and uncertain-delivery contract. Cost: execution still requires an agent with approved browser access.

Independent review: one P2 missing baseline-blocker comparison reproduced by a failing test. Fixed with baseline_blockers/new_blockers and newly_blocked_products. Added five invalid/missing price-status cases. Focused suite 30 passed; initial full app suite 521 passed before these fixes. No additional important review findings; live platform behavior and storefront/settlement remain outside static code verification.
