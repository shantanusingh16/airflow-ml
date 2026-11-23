# segment-c — build inputs

- Base clip (not in git; `assets/` is ignored): copy `/inputs/artifacts/t_13de095d/capture-4/out/segment-c.mp4`
  to `assets/segment-c.mp4` — sha256 `8810b1eb14a770bb3f61e238e2783511664957ad9a7ef4d2417a60cdf45d1e0f`,
  H.264 High yuv420p 1920×1080@30, 831 frames, 27.70 s, no audio. Used 1:1 (no trim, rate change, crop).
- `observed.json` — byte-identical to `factory/t_13de095d/capture-4:artifacts/capture-4/observed.json`
  (sha256 `b134b92a0570a4beab7805d3d9f30dcbae61208c5f53366a43b4870f06d1b847`). Only numeric source.
- Cuts (measured by frame diff): C1a→C1b frame 106 = 3.533 s; C1→C2 frame 294 = 9.800 s; C2→C3 frame 556 = 18.533 s.
  C2 row click ~12.47 s (Object Info open by 12.6 s), Preview click ~17.93 s. C3 wheel scroll 21.17–22.90 s, then static.
- Callout geometry measured from source pixels:
  C1b log L54 glyph rows y 999–1010 (L53 y 981–992, L55 y 1017–1027), text x 737–1578 → box border in the gaps
  (x 731–1588, y 995–1015). C2 name cell glyphs x 364–551 (565 hovered), y 292–307 → box x 354–582, y 285–315.
- Caption positions per shot (bottom of frame, over empty UI): C1 left Grid panel (a centred bar would cover
  log lines 46–55), C2 object-list body (left of the Object Info panel), C3 dialog margin left of the pages.
- Render: `npx hyperframes render --quality delivery -o renders/segment-c.mp4` (renders/ is ignored).
