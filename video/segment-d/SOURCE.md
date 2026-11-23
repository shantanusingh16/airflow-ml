# segment-d — build inputs

- Base clip (not in git; `assets/` is ignored): copy `/inputs/artifacts/t_fd8b1574/capture-5/out/capture-5.mp4`
  to `assets/capture-5.mp4` — sha256 `05e5671544fbbc6c55f214dc7bdd58ee0296519c54b11f1e866f7da539350955`,
  H.264 1920×1080@30, 692 frames, 23.066667 s, no audio. Used 1:1 (no trim, rate change, crop).
- `observed.json` — byte-identical to `factory/t_fd8b1574/capture-5:out/observed.json`
  (sha256 `adce5b9a96986c72b79f39529b5c77b395f0ee723d44ab8e30bb868cff629fec`). Only numeric source.
- Cut (measured): last D1 frame 12.467 s; white/loading frames 12.5–12.77 s; D2 settled 12.8 s (keyframe at 12.5 s).
- Callout geometry measured from source pixels: D1 L25 glyph rows y 669–680 (text ends x 1189), L27–29 y 705–752
  (ends x 1094), L24 warning y 651–662 untouched; D2 Success badge x 854–940 y 349–374, Duration text x 1286–1339 y 357–366.
- Render: `npx hyperframes render --quality delivery -o renders/segment-d.mp4` (renders/ is ignored).

## Re-render for assembly (card t_31cfb2ff, operator CF-1 "soften both", 2026-11-23)

- Extracted read-only from `factory/t_3735e1d8/video-3` (`git archive … video/segment-d`); base clip copied from
  `/inputs/artifacts/t_3735e1d8/video-3/video/segment-d/assets/capture-5.mp4` (sha256 05e56715…0955, verified).
- Only change: D2 caption line 2 `1000 images, split-safe` → `1000 images, near-dup-checked, cluster-aware splits`
  (`compositions/captions.html`). At 28 px the line widened the 760 px min-width bar to ≈782 px, so `#cap-d2 .l2`
  is 27 px with −0.1 px tracking: bar stays x580–1339, y884–991 (measured). D1 caption and every other overlay untouched.
- Diff vs the approved render (aefe3362…a2ab): lossless PNG-sequence renders of old vs new project differ only inside
  the caption bar, frames 376–691 (local ≥ 12.533 s); 0 differing pixels outside it in all 692 frames. Delivery MP4:
  same profile/SPS/PPS, 692 frames, frames 0–375 bit-identical.
