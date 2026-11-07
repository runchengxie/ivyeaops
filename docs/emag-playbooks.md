# eMAG source-linked operation playbooks

[简体中文](zh-CN/emag-playbooks.md)

Use the structured playbook panel to investigate existing-stock problems, prepare local changes and retain the evidence behind manual decisions. The panel extends the eMAG Listing, playbook and analysis workspaces. It does not submit product content, merge variants, buy advertising, purchase stock or create warehouse receptions.

## Workflows

| Workflow | Inputs and result | Important boundary |
|---|---|---|
| Repair guidance | Current snapshot issues link to relevant checks and training references | A repair suggestion is not a verified diagnosis or a platform action |
| Listing readiness | Product facts, language and explicit manual checks for category access, contract, attributes, images and barcode | Unknown checks stay unknown; no automatic visual or legal certification |
| Variant proposal | Existing product IDs, distinguishing values and shared family metadata | Proposed members must be reviewed; nothing is merged remotely |
| Comparable offer | Source URL, observation time, tax-inclusive price, specification and delivery basis | Observations do not establish market sales, demand or a recommended price |
| Advertising review | Campaign and Adset states, explicit prerequisites and optional period-bound results | Manual observations only; no recharge, activation, bidding or profit claim |
| Inbound packing | Reception reference, explicit address confirmation, boxes, quantities and barcodes | No current warehouse address is supplied by default and no reception is submitted |
| Cost evidence | Named calculator input, recorded amount/unit, source, observation time, validity and scope | Evidence is saved separately; it neither updates nor verifies the commerce calculator |

The new panel defaults to English and offers a persisted English/Chinese language selector. This is scoped to the panel; it does not imply full-product localization.

## A useful first pass

1. Open the playbook workspace for the store's latest imported snapshot. Prioritize stocked products with captured availability or documentation blockers.
2. Read the issue and associated training references. Inspect the seller portal before asserting an actual root cause.
3. Record the product facts and only confirm checks that have evidence. Preserve a failed check rather than changing it to unknown to make a record look complete.
4. Save a local revision. Use the existing draft and manual processing workflows for actual operator work; saving a playbook does not advance approval or execution states.
5. After an operator changes the seller portal, collect a new snapshot and review again. Old records remain labelled with their old source version and must be reconfirmed against the new snapshot.

## Evidence and results

A checkbox or a supplied number records an operator assertion. It is not proof of marketplace approval, actual stock receipt, paid refunds or advertising attribution. A passed assessment means only that the submitted data satisfied that check. Missing inputs must not become zero. Numeric inputs are bounded to one billion and at most 12 fractional places. Variant members and nonempty inbound lines must include the selected primary product. Listing image and barcode checks are explicitly manual; the historical documents' image dimensions, EAN examples and fees are not hard-coded as current platform requirements.

Advertising results require a valid start/end period. CPC needs known spend and nonzero clicks; ROAS needs known revenue and nonzero spend. ROAS is a ratio of the entered figures, not accounting profit. Campaign and Adset states are separate observations. Report dates and account attribution must be checked by the operator.

Cost evidence should name the exact field in the existing cost calculator, preserve its unit, identify the source and state when and where it applies. Compare the evidence value with the separately saved calculator input. Do not reuse an old training sheet's unexplained conversion factors as current VAT, commission or exchange-rate rules.

## Storage and access

The administrator API reads the store's immutable snapshot and stores local records under the configured `IVYEA_OPS_DATA_DIR`. Every saved revision is bound to store, snapshot, product and authenticated operator. Updates require the current record revision and current snapshot; conflicting or stale submissions are rejected instead of overwriting another operator's work. The ledger keeps prior revisions. History is paginated in batches of up to 500; `before_sequence` requests older entries and `records_next_before` identifies the next cursor. Only the globally latest revision on the active snapshot is current. No marketplace writer is called by these routes.

- `GET /api/emag/stores/{store_id}/playbooks`
- `POST /api/emag/stores/{store_id}/playbooks/records`

Private observations, notes and original training documents must remain outside Git. Back up the application data directory using the project's existing procedures. The local source archive is separate from the application ledger and is not uploaded automatically.

## Training sources and freshness

The registry contains concise generic descriptions and document/page locators. Its source material includes category access, single/batch Listing, competitor price comparison, FBE packing, an advertising deck dated July 2024, and a seller selection workbook whose fee assumptions were not documented. Dates that were not established remain unknown. Training citations explain the origin of a checklist, not its current official validity.

Keep the original PDFs, PPTX, workbook and online-document snapshots in private storage. A locator should resolve to a source title and page/slide or sheet within that archive. Do not add personal machine paths, private sharing tokens or original materials to the public repository. The video directory's external courses and inaccessible supplementary PDFs were not read and cannot supply rules.

See [workspace boundaries](emag-workspace.md), [business evidence](emag-business-evidence.md) and [manual issue handling](emag-operations.md).
