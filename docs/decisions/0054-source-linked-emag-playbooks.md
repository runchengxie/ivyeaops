# ADR 0054 Source-linked local eMAG playbooks

- Date: 2026-11-07
- Status: Accepted
- Basis: Approved source-linked operations scope in the user conversation.

## Context

Existing-stock operations already have immutable evidence snapshots, a conservative cost calculator, free-text drafts and manual issue states. Training materials provide practical repair, Listing, variant, pricing, advertising and packing checks, but some rules are dated and several linked attachments are inaccessible.

## Decision

Add validated local records with pure deterministic assessments and a small source registry. Bind every revision to the current store snapshot and authenticated administrator. Surface the workflows in the existing React App. Keep operator confirmations distinct from observed platform data. Do not introduce marketplace execution, remote URL fetching or historical fee defaults.

## Alternatives

A separate tutorial reader would preserve documents but would not connect them to product work. A marketplace writer would require verified current contracts and separate execution boundaries. A generic JSON editor would leave operators to discover schemas and would not provide useful check-level feedback. The selected structured local forms reuse current evidence boundaries without these costs.

## Consequences

Operators must supply missing data and reconfirm records after source changes. Check status describes supplied evidence rather than certifying marketplace compliance. The application ledger and private original-document archive remain separate. Source metadata and paired documentation need maintenance when requirements change. English/Chinese localization covers the new panel only.
