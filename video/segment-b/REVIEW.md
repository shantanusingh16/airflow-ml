# segment-b — snapshot review (draft render, 902 frames)

- Base fidelity: per-frame diff vs source in an overlay-free crop (x 460–1900, y 240–540): 902/902 frames,
  worst 2.13/255 mean abs (encode noise only) → no frozen/shifted frames despite 8 s source GOP.
- Occlusion: 0 pixels changed (>60 levels) on B2 L10–L13 + Post Execute, B3b L14–L18, all three grid badges,
  both tooltips, and the duration-axis labels.
- B1 (0–9.1): chip "B1 · Verify"; caption "verify_upload ✓"; callout box on verify_upload badge 0.5–7.45, out
  before the 7.567 cut. Box hugs the badge; cursor ring touches its right edge from 4.33 s (cursor, not text).
- B2 (9.1–17.6): chip "B2 · Verify log"; caption "1000 images verified"; box around L11–L13 9.4–17.45, label
  "verify_upload counts" in empty space right of L13. Cursor not called out.
- B3 (17.6–30.067): chip "B3 · Ingest"; caption "ingest_voc12: 1000 images"; B3a box on ingest_voc12 badge
  18.7–22.75 (grid settled 18.6, cut 22.867); B3b box on L17 INGEST OK 24.5–end, L15 commit line untouched.
- Legibility: captions white 34 px bold on rgba(17,24,39,.92) pill over the near-white UI; chips 19 px on the same.
- check: 0 errors; warnings = film_silent (spec: silent segment) and text_below_floor on 18 px callout labels
  (spec: small labels; they must fit beside 13 px log lines).
