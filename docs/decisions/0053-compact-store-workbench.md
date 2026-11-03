# 0053 — Compact store workbench and scoped embedded conversation

Date: 2026-11-04

The daily interface previously spread store evidence, suggested checks and the Agent across several pages. Make `/workbench` the common landing page: evidence metrics and at most five prioritized observations on the left, embedded Console on the right. Keep detail routes and their permission boundaries available under More. Preserve the workbench while visiting detail routes.

Reuse Console streaming, permissions, stop and restoration instead of introducing another Agent client. Optional context/draft/busy props leave existing Console consumers unchanged. Bind each conversation to an explicit store and original snapshot; selecting a different store does not rebind or clear a live conversation. Switching or opening history requires an idle conversation. Each explicit new/history transition creates an isolated Console runtime, so pending attachments and previous session IDs cannot cross stores; failed history restores show an error and clear the old runtime. Pending queues are namespaced by user/store and a new unbound session does not restore the generic new-session queue. Store only per-user session/scope references locally, not snapshot bodies.

The shared workbench presentation accepts its chat component and account actions. Production provides authenticated Agent bindings; the public Pages demo provides a labelled synthetic conversation with memory-only state. The demo retains its network-denying CSP and never loads the production Agent component. This keeps the interface consistent without representing preset demo text as a model response.

Tradeoffs: narrow viewports use tabs and panel scrolling; the compact queue is a bounded inspection priority, not a forecast, recommendation to change a specific price, or execution approval. Existing detail workflows remain necessary for investigation and records.
