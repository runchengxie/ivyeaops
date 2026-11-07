# 0055: Keep market observations separate from seller snapshots

Date: 2026-11-08

## Decision

Store opportunities and competitor quotes in a private immutable SQLite revision ledger, independently from own-store collection and the existing execution/approval APIs. Bind local writes to a current seller snapshot, retain source/time/currency/tax metadata and match only exact PNK identities. Compare historical quotes only under equivalent explicit conditions. CSV imports validate as one atomic operation.

Extend existing commerce scenarios rather than add a second cost model. Reverse prices use the same gross-price commission assumption and round upward; incomplete or infeasible results remain unknown.

## Alternatives and consequences

A live market feed would require verified external authorization, field semantics and coverage; none is assumed from a public dashboard description. Manual and authorized CSV observations work now but do not provide complete or continuous market coverage. The UI limits displayed history to 2000 revisions and reports truncation; stored evidence is not deleted. Separate research approval labels do not authorize execution. No new dependency is required.
