# segment-b — build inputs

- Base clip (not in git; `assets/` is ignored): copy `/inputs/artifacts/t_8a350dbc/capture-3c/out/segment-b.mp4`
  to `assets/segment-b.mp4` — sha256 `9b97cdc42c8cf24b38bdd9763d3ff273208f3e27371c89b558d78e869374b832`,
  1,077,128 B, H.264 1920×1080@30, 902 frames, 30.066667 s, no audio. Used 1:1 (no trim, rate change, crop).
- `observed.json` — byte-identical to `factory/t_8a350dbc/capture-3c:artifacts/capture-3/observed.json`
  (sha256 `3358def03b3541ef82ec20813f876190bf93ac2c2ff83054c3d460020dd41f95`). Only numeric source:
  `images_verified`=1000 → B2 caption `{n_verified}`; `images_ingested`=1000 → B3 caption `{n_ingested}`.
- Cuts (measured, per-frame diff): B1 grid 0–7.567 (verify_upload tooltip 1.0–4.2); white/loading 7.567–9.133;
  B2 log static 9.133–17.6; white 17.6–17.87; B3a grid rendering 17.87–18.6, ingest_voc12 tooltip 19.8–22.867;
  white/loading 22.867–24.367; B3b log static 24.367–30.067.
- Callout geometry from source pixels: grid badges x 407–420 (upload y 257–270, verify 276–289, ingest 296–309),
  tooltip arrows from y 294 (B1) / 313 (B3a). B2 glyph rows L10 543–554, L11 561–572, L12 579–590,
  L13 597–608 (ends x 1419), Post Execute 613–624. B3b L14 615–626, L15 633–644 (DeepLake commit, untouched),
  L16 651–662 (ends x 1527), L17 669–680 (ends x 1397), L18 687–698. Box borders run only through the
  6 px inter-line gaps.
- Render: `npx hyperframes render --quality delivery -o renders/segment-b.mp4` (renders/ is ignored).
