# Minimal workbench refinement

User requests a more intuitive interaction and an explicitly minimal visual style. Retain the approved store overview / priorities / permanent right chat structure. Use a monochrome palette, fewer borders/icons, plain Chinese headings and at most three visible priorities; details retain provenance and complete workflows. Preserve store isolation and explicit send.

Plan (inline execution, TDD and independent review):
- [x] Reproduce a browser failure for the minimal composer and bounded visible priorities.
- [x] Remove redundant labels/decorations and move technical snapshot/method copy into Data information.
- [x] Add opt-in minimal Console/Composer presentation used only by the workbench: text input, send/stop, and collapsed Options. Preserve visible effective approval/goal/persona status and all existing controls under Options.
- [x] Keep the same simplified styling and wording in the synthetic Pages demo; shorten suggested questions while retaining exact references.
- [ ] Verify real App and built demo on desktop/mobile, existing isolation/stop/history contracts, types/builds/security/doc links; independent review.
- [ ] PR/CI/merge, update local UI, publish and verify Pages, clean task branch/worktree under standing authorization.

Review focus: hiding controls must not hide effective write/goal/persona state; slash model command must open hidden options; no auto-send; original Console/dock default must stay unchanged; provenance/unknown values and all-issues entry remain available.

Review: no blocking issues; updated both usage translations to match Ask assistant / 问助手. New browser regression failed before implementation and now passes (collapsed controls, visible full permission, /model, three priorities, mobile and original Console). Existing send/stop/scope/history/isolation and synthetic demo behavior pass. No deferred review findings. Final production/demo builds and hosted CI/publication are verified before delivery.
