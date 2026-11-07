# eMAG evidence playbooks

## Approved scope

Implement the six opportunities approved in the conversation: source-linked repair guidance, structured Listing readiness, manual variant proposals, comparable-offer observations, advertising readiness and results, and inbound packing checks. Add cost-input provenance and contextual training references. Existing-stock recovery remains the priority. Marketplace execution, procurement, advertising payments, automatic merging and inbound submissions are excluded.

## Approach

Extend the current snapshot-bound administrator workspace with one local playbook ledger and deterministic assessments. Reuse immutable snapshots, existing issues and authentication. Keep the existing free-text drafts and commerce calculator intact. Structured local records are preferable to unverified marketplace writers or another generic chat interface.

The new workspace is a panel inside the real eMAG tools/playbook/Listing pages. English is the default for the new panel, with a persisted English/Chinese selector. All new UI copy belongs in locale catalogs. Existing legacy page localization is outside scope.

## Backend contract

New pure module `emag_playbook_rules.py`: `sources() -> list`, `repair_guidance(snapshot) -> list`, `validate_payload(kind, payload, offers) -> dict`, `assess(kind, payload, offers) -> dict`. All record payloads reject unknown fields, bound lengths/list sizes and invalid numeric/date/URL values. No fetching user URLs. Assessments return `{checks: [{key, status, source_ids}], source_ids, metrics}`. Check status is `passed`, `failed`, or `unknown`. Manual confirmation is not platform verification.

New service `emag_playbooks.py`: `view(store_id)` and `save(store_id, snapshot_id, kind, product_id, payload, actor, record_id=None, revision=0)`. Private SQLite file under configured data_dir, store-scoped immutable revision history, snapshot_guard held during writes, reject stale snapshots, absent products, mismatched store/kind/product updates, and optimistic revision conflicts. GET marks historical records stale and never treats them as current checks. All results carry `marketplace_writes=false`.

GET `/api/emag/stores/{store_id}/playbooks` returns `{store_id,snapshot_id,captured_at,marketplace_writes:false,products:[{product_id,name,sku,stock}],repairs:[{product_id,issue_id,reason,rule_ids,source_ids}],sources,records}`. Records contain `{record_id,kind,product_id,snapshot_id,revision,payload,assessment,actor,updated_at,stale}`. POST `/api/emag/stores/{store_id}/playbooks/records` accepts `{snapshot_id,kind,product_id,payload,record_id:null|str,revision:int}`. Admin dependency, server-derived actor, 404 for missing workspace, 409 for conflicts, 422 for schema/value validation. No endpoints call marketplace writers.

## Payloads

All kinds have optional `note` (max 2000). Product IDs are strings from the current store snapshot. Decimal fields are nonnegative numeric strings, finite and bounded. Optional numeric fields omitted/blank mean unknown, never zero. Links must be HTTPS without userinfo; arbitrary external URLs are stored only, never fetched. ISO dates require timezone. Lists max 100 (images max 10). Unknown tri-state values rejected; tri-state = `unknown|confirmed|failed`.

- `listing`: title, description (max 40000), brand, model, color, size, package_contents, ean, source_language, content_language, evidence_url; manual tri-state category_access, commission_contract, mandatory_complete, title_matches, images_match, main_image_white, main_image_no_overlay, ean_matches, dimensions_confirmed. Missing evidence remains unknown. No old image dimensions/EAN digit rules hard-coded as current requirements.
- `variant`: family_name, family_id, family_type (`color|size|other`), members `[{product_id,value}]`. At least two distinct products, each must exist. Duplicate member IDs/values rejected. Missing family metadata is unknown, not an executable proposal. No title similarity auto-merging.
- `competitor`: url, observed_at, price_gross_ron, delivery (`emag_delivery|seller|unknown`), specification, comparable tri-state. Observation records do not establish sales, demand or a target price.
- `ads`: campaign_id, adset_id, campaign_status and adset_status (`unknown|draft|active|paused`), buy_button and listing_ready tri-state, balance_ron, budget_ron, impressions, clicks, spend_ron, orders, revenue_ron, period_start, period_end. Counts integral, clicks cannot exceed known impressions, end after start, both period bounds required for result metrics. Readiness checks use known snapshot stock plus explicit manual inputs. Both statuses must be active; unknown stays unknown. CPC=spend/clicks and ROAS=revenue/spend only with known nonzero denominators and a period, no profit claim or guaranteed performance.
- `inbound`: reception_id, address_confirmed tri-state, box_count positive integer if provided, tracking_number, items `[{product_id,ean,expected_ean,quantity,box}]` with positive integer quantities and box numbers. Unique product+box lines, consistent ean/expected_ean for a product, no same barcode across different products. Missing/mismatched barcode is unknown/failed; boxes cannot exceed known box_count. No default warehouse address.
- `cost_evidence`: cost_field (existing COSTS names), value, unit (`CNY|RON|percent|RON_per_CNY`), source_url, observed_at, valid_until, scope. No automatic update of commerce inputs or recomputation. Explicitly display it as a separate evidence record that needs comparison with saved calculator input. Valid-until after observed-at; no official fee claim.

## Knowledge references

Generic metadata and concise paraphrases only; do not commit private PDFs, tokenized URLs, supplier observations or personal data. Stable source IDs for category, Listing, batch import, pricing, FBE, ads and selection. Include historical version/unknown date and review caveat. Source locators map to the user's private local archive but do not include machine paths. External video and inaccessible supplement bodies cannot supply rules. Exact dated tax rates, bids and warehouse addresses are never current defaults.

## Verification

Test unknown versus zero, malformed data, mixed-store/product identities, stale/revision conflicts, concurrent update behavior, assessment refresh after a new snapshot, no cross-store records, no marketplace calls, safe URL rendering and bilingual catalog parity. Frontend save/error/history flows must work in real App harness. Run full backend and client CI-equivalent checks, preserve baseline failures, and require remote checks against the merged result before integration/cleanup.
