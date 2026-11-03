---
name: emag-price-validation
description: Inspect eMAG price rejection, preview a current-price validation, submit only explicitly approved offers through an existing browser connection, and review later evidence. Use with IvyeaOps read MCP and an authorized browser MCP; no browser executor is bundled.
---

# Existing-price validation and clearance follow-up

Use `ivyea_emag_clearance_review(store_id, baseline_snapshot_id?)` with a read token. It reads imported snapshots, not live state. Keep snapshot/time/source/coverage and exact per-row field references. Use its queue to prioritize existing stock, not to assume permission or recommend a new price. `approved` is always false. If the tool is unavailable, use snapshot inspection and state that the review is advisory.

Keep one official Playwright MCP connection for the task. Inspect tools/list: target/ref parameters differ by version. Use the user's installed browser profile and private configuration; never request/export cookies or print extension tokens. Do not launch a new MCP process for every action. Verify seller and RO platform from the rendered page, then use the observed My offers / Prices menu. Read the actual page before choosing locators.

For each offer, make a preview with store, snapshot, offer ID, SKU, PNK, exact current net RON price, rejection message, and intended operation: validate this unchanged price. Obtain explicit user approval of those fields before a consequential submission. Existing local issue approval and a queued row do not authorize browser writes. Recheck fresh page identity and current price; abort on drift or unknown values. Do not infer that a seller's min/max is the platform's accepted range.

IMPORTANT: selections can survive filter changes. A DOM containing one filtered row does not prove the global selection contains one item. Start each offer from a fresh navigation/reload of the observed price-page URL, clear previous selections, and verify the page's selected count and chosen identity. If the global count cannot be verified, do not submit; hand the scoped action to the user. Do not perform multi-item submission as a fallback. Do not use a hidden/duplicate confirmation button. Inspect only the visible confirmation dialog and its text. Do not fill or save a new price while validating the existing amount.

Persist a private pre-submit record and confirmation snapshot before clicking the final visible confirmation once. After the click, record the actual success/error text and item count. A click is not acceptance. A timeout, count mismatch or unknown outcome stops writes; do not replay. Read current evidence and investigate selected scope. If the website says changes take at least an hour, record the wait requirement and arrange an authorized read-only follow-up, not repeated validation.

Use a newer complete snapshot with the explicit pre-action baseline for comparison. A disappeared price-rejection code, available-looking UI or stock decrease does not prove storefront purchaseability, sales, profit, settled cash, or the causal effect of this operation. Verify these separately. Preserve order/return sample coverage. Missing or identity-mismatched products are excluded from deltas and never treated as zero stock.

For content conflicts, create local physical-verification checklists and conservative drafts. Catalogue images do not prove frequency, dimensions, accessories, certification or medical claims. No procurement and no owner assignment unless the user changes those constraints.
