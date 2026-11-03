# Compact store workbench design

## Intent
Provide one everyday eMAG RO screen for store condition, prioritized adjustments and an always-visible AI conversation. The user selected a permanent right-hand conversation instead of a popup.

## Approach
Replace the everyday landing view with a compact dashboard, reusing collected evidence and the existing embedded Console. Keep detailed tools reachable through a secondary menu. A floating-only chat was rejected by the user; a new standalone chat implementation would duplicate established streaming, approval and stop behavior.

## Layout and behavior
- Desktop target: 1366 x 768 and larger. A slim header holds store selection, snapshot freshness, refresh and More/Settings. No large persistent navigation or separate conversation-history sidebar on the compact screen.
- Left area: four evidence-backed metrics (products, observed orders, known stock, observed issues), then a short prioritized adjustments list. Show at most five items with internal scrolling, reason and next step. Source timestamp remains visible; unknown values stay unknown.
- Right area: permanent AI conversation reusing embedded Console, new/history controls, streaming, stop and existing permission/approval controls. Model and attachment controls stay available without dominating the empty view.
- Clicking Analyze on a suggestion prefills a scoped prompt containing store, snapshot and exact issue/product references; the user sends it. No automatic model call on load, store change or suggestion selection.
- Conversations remain explicitly associated with the store they were started for; switching stores must not silently mix old conversation context with a different store. Preserve ongoing conversations and require an explicit new conversation/rebind when appropriate.
- Defaults open the compact screen after login. Existing detail routes remain available through More, with their existing access rules and data.
- Narrow screens use Overview / Suggestions / Conversation tabs. Conversation state stays mounted across tabs. Large text and zoom can scroll within panels rather than clipping content.

## Boundaries
No new platform writes, automatic repricing, collection scheduling, provider configuration changes or data migration. Display only actual snapshot evidence and observed-window metrics. Existing configured AI Agent is reused; offline/unconfigured state is shown accurately.

## Validation
Behavior tests for priority sorting, unknown values, prompt scoping and store switches. Real App harness checks at 1366x768, 1440x900 and 390x844, including computed overflow, loading/empty/error states, conversation send/stop and details navigation. Run applicable frontend and backend checks; independent review and standing-authorized PR/merge/cleanup.
