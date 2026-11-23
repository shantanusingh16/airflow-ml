# t_61fa2737 / video-3

## Prompt as dispatched

````
---
factory:
  base: HEAD
  inputs:
  - artifacts/t_13de095d/capture-4
---

# Task: voc12_demo UX demo video — segment C compose (DEDUPLICATE)

Compose **segment C** of the voc12_demo UX demo: add **HyperFrames overlays/captions** to the already-captured,
QA-approved clip. You deliver **one silent MP4** — VO and music are mixed later at assembly. All inputs are
artifacts (mounted read-only under `/inputs`); there is **no staging access** and no staging is needed.

## Inputs (mounted)

- Source clip: `/inputs/artifacts/t_13de095d/capture-4/out/segment-c.mp4`
  — H.264 (High, yuv420p), 1920×1080 @ 30 fps (30/1), 831 frames, 27.70 s, 1,104,897 B, sha256
  `8810b1eb14a770bb3f61e238e2783511664957ad9a7ef4d2417a60cdf45d1e0f` (verified by the capture worker and by
  QA; do not alter it).
- Raw per-shot pieces (reference only, to pin shot boundaries if the sample frames are ambiguous):
  `/inputs/artifacts/t_13de095d/capture-4/demo/capture-4/out/pieces/1..4.mp4` (+ `1raw`/`3raw`). Do not use
  them in the output — the composed clip is built on `segment-c.mp4` only.
- `observed.json` — the single source of truth for every number in this window. NOTE: this window's artifact
  directory contains only the MP4s, so the byte-identical observed.json (sha256
  `b134b92a0570a4beab7805d3d9f30dcbae61208c5f53366a43b4870f06d1b847`, verified identical to the blob committed on
  the capture branch) is inlined below. Write it into the build folder verbatim and treat it as the
  ONLY numeric source:

```json
{
  "window": "capture-4",
  "segment": "C (DEDUPLICATE)",
  "clip": "out/segment-c.mp4 (27.70 s, 1920x1080, 30 fps, H.264, no audio)",
  "shots": {
    "C1a": "0.00-3.53 s  Airflow run page /dags/voc12_demo/runs/<run_id> with Grid panel (left) -> click on the embed_fastdup grid cell",
    "C1b": "3.53-9.80 s  embed_fastdup task page, Logs tab, scrolled to bottom before the take (static hold)",
    "C2":  "9.80-18.53 s MinIO console ml-artifacts/analysis/<run_id>/ -> click object row -> Object Info panel -> click Actions > Preview",
    "C3":  "18.53-27.70 s PDF preview at top (pages 1-2), one smooth wheel scroll (~21.1-23.3 s) to page 3, hold 23.3-27.7 s"
  },
  "dag_id": { "value": "voc12_demo", "where": "C1a+C1b breadcrumb 'Dag voc12_demo' (top-left)" },
  "run_id": { "value": "manual__2026-11-23T01:00:57.988475+00:00", "where": "C1a run header title + breadcrumb; C1b breadcrumb 'Dag Run'; C2 breadcrumb; C3 preview dialog title" },
  "run_state": { "value": "Success", "where": "C1a green badge next to the run id in the run header" },
  "run_duration": { "value": "00:17:02", "where": "C1a run header 'Duration'; also Grid duration axis label (00:17:02)" },
  "grid_task_states": {
    "value": ["success", "success", "success", "success", "success"],
    "tasks": ["upload_voc12", "verify_upload", "ingest_voc12", "embed_fastdup", "cluster_split"],
    "where": "C1a Grid panel (left, x~413, y 263-343): 5 green check badges in the run column (DOM data-testid grid-<run_id>-<task>, task-state-badge; frame pixel RGB ~(0-9,106-115,3-12)); same screen: Task Instances table shows 'Success' for all 5 tasks",
    "note": "Grid RENDERED in this window (0 WebSocket connections, but grid data loaded) - Runs-table fallback NOT used"
  },
  "fastdup_version": { "value": "2.54", "where": "C1b log line 19 'fastdup 2.54 over 1000 images ...'" },
  "images_embedded": { "value": 1000, "where": "C1b log line 39 'Dataset contains 1000 images' and line 54 'EMBED OK: 1000 images, ...'" },
  "outliers": { "value": 69, "where": "C1b log line 41 'Outliers: 6.90% (69) of images are possible outliers ...'" },
  "outliers_pct": { "value": "6.90%", "where": "C1b log line 41" },
  "embedding_dim": { "value": 576, "where": "C1b log line 48 'fastdup embeddings done in 1s (dim=576)' (also line 51 'dinov2_embedding (576-dim)')" },
  "dup_groups": { "value": 1, "where": "C1b log line 54 'EMBED OK: 1000 images, 1 dup groups; manifest data/<run_id>/voc12_embed_manifest.json'; C3 page 3 title 'Duplicate groups (1) — top 20 by size' (canvas-rendered)" },
  "pdf_report_key": { "value": "s3://ml-artifacts/analysis/manual__2026-11-23T01:00:57.988475+00:00/voc12_embed_report.pdf", "where": "C1b log line 53 'PDF report published: ...'" },
  "report_prefix": { "value": "analysis/manual__2026-11-23T01:00:57.988475+00:00", "where": "C2 breadcrumb 'ml-artifacts / analysis / manual__2026-11-23T01:00:57.988475+00:00'; C3 dialog title" },
  "report_object_name": { "value": "voc12_embed_report.pdf", "where": "C2 object row + Object Info 'Name'" },
  "report_size": { "value": "74.0 KiB", "where": "C2 object row 'Size' column + Object Info 'Size'" },
  "report_last_modified": { "value": "Today, 01:14", "where": "C2 object row 'Last Modified' (Object Info panel shows '14 hours ago')" },
  "report_etag": { "value": "6f152d0513c33dadb17ac3dfed760001", "where": "C2 Object Info 'ETAG'" },
  "report_page3": {
    "value": "Duplicate groups (1) — top 20 by size / group 828: 2 images",
    "where": "C3 hold 23.3-27.7 s: page 3 canvas at y 120-696 of the frame (pages 1-2 above, page 4 histograms below; dialog scrollTop 907)",
    "note": "Page 3 is text-only (title + group list) - per dags/jobs/embed_voc12.py; no thumbnails are drawn on it and the 'most similar pair' image page is not present in this PDF (4 pages). No VOC images appear anywhere in the clip."
  },
  "reference_only_not_dataset_counts": { "value": "113.8 MiB - 2734 Objects", "where": "C2 MinIO bucket header (bucket totals; never caption as dataset counts)" },
  "internal_hostname_in_frame": { "value": false, "where": "C1b: log source-URL line (airflow-worker:8793) is line 1, scrolled out of frame (visible lines 16-55); checked before and after the hold" }
}
```

Placeholder mapping (compose contract): `{n_dup_groups}` → `dup_groups.value` = 1; `{run_id}` → `run_id.value` =
`manual__2026-11-23T01:00:57.988475+00:00`.

## What the clip contains (QA-verified, presentation order C1 → C2 → C3)

Exact timing from observed.json `shots` (verify against sample frames; the clip is the ground truth):

| Shot | Time | On screen |
|------|------|-----------|
| C1a | 0.00–3.53 s | Airflow run page `/dags/voc12_demo/runs/<run_id>`: run header (run id, **Success** badge, Duration `00:17:02`) + Grid panel (left) with 5 green task cells → cursor click on the `embed_fastdup` cell. |
| C1b | 3.53–9.80 s | `embed_fastdup` task page, Logs tab, **scrolled to the bottom before the take — static hold**. In frame (lines 16–55): `fastdup 2.54 over 1000 images`, `Dataset contains 1000 images`, `Outliers: 6.90% (69)`, `fastdup embeddings done in 1s (dim=576)`, `PDF report published: analysis/manual__.../voc12_embed_report.pdf`, and the duplicate-group line **`EMBED OK: 1000 images, 1 dup groups`**. The source-URL line (`airflow-worker:8793`, line 1) is scrolled out of frame. |
| C2 | 9.80–18.53 s | MinIO console, bucket `ml-artifacts`, breadcrumb `analysis / manual__2026-11-23T01:00:57.988475+00:00`: object row **`voc12_embed_report.pdf`** (74.0 KiB, Today 01:14) → click row → **Object Info** panel (Name / Size / Last Modified / ETAG) → click Actions > Preview at the end of the shot. Bucket header shows `113.8 MiB - 2734 Objects` (bucket totals — reference only, never caption as dataset counts). |
| C3 | 18.53–27.70 s | Report PDF preview dialog opens at top scroll (page 1 summary + page 2 PCA) → **one smooth wheel scroll (~21.1–23.3 s)** to page 3 → **hold 23.3–27.7 s** on the duplicate-groups table page: title `Duplicate groups (1) — top 20 by size`, line `group 828: 2 images`. Page 3 is **text-only** (no thumbnails); report pages are canvas-rendered (no selectable text) — verify page content by pixels/geometry, not a text layer. |

## Overlays to build (HyperFrames, on the captured clip only)

Use the **hyperframes skill**. Build the HyperFrames project in folder **`video/segment-c/`** at the repo root
(source clip + observed.json copied into that folder for the build).

Per shot, exactly these overlay elements:

1. **Title chip** (small chip, top corner, constant for the shot):
   - C1 (C1a+C1b): `C1 · Deduplicate`
   - C2: `C2 · Report in MinIO`
   - C3: `C3 · Dedup report`
2. **Caption bar** (bottom of frame, always on for the whole segment — v2 copy, filled STRICTLY from
   observed.json):
   - C1 (0.00–9.80 s, both sub-shots): `1 near-dup group` — `{n_dup_groups}` → `dup_groups.value` = 1, rendered
     **singular** per the v2 compose note (value is 1 in this run). Single line.
   - C2 (9.80–18.53 s): the filled path `analysis/{run_id}/voc12_embed_report.pdf` rendered as **two lines**:
     line 1 `analysis/`, line 2 `manual__2026-11-23T01:00:57.988475+00:00/voc12_embed_report.pdf`
     (`{run_id}` → `run_id.value` = `manual__2026-11-23T01:00:57.988475+00:00`). The two lines together are the
     complete path, identical to the on-screen MinIO breadcrumb — grounded, not invented.
   - C3 (18.53–27.70 s): `voc12_embed_report.pdf · dup groups` (no placeholders).
3. **Callout boxes** (thin border + small label, pointer to the element; appear only while the element is in
   frame; must not cover any on-screen text). Time each callout to the actual frames (extract sample frames per
   shot to place them). Exactly **two** callouts in this segment:
   - C1b: the duplicate-group log line — `EMBED OK: 1000 images, 1 dup groups` (line 54) in the static
     `embed_fastdup` log hold, with the fastdup summary block above it (2.54 / 1000 images / dim=576 / outliers /
     PDF-published line) staying fully legible around the callout.
   - C2: the `voc12_embed_report.pdf` object row in the MinIO console (the 74.0 KiB row) — do not cover the
     row or the Object Info panel values.
   - C3: **no callout** — the report's own page layout stays clean (chip + caption only).

## Hard rules

1. **Never re-render, speed-change, crop the content area, or alter the captured UI.** The base video is the
   source clip untouched; overlays are composited on top only. Output length = input length (27.70 s, 831
   frames).
2. **No external images or footage** of any kind — overlays are text/chips/boxes only. Licensing: VOC images
   appear in this clip only as report-page content inside the report's own layout (page 3 in this run is
   text-only); overlays must NOT crop a single VOC photo into a full-screen frame, zoom into report cells, or
   introduce any VOC image content.
3. **Silent segment** — no VO, no music, no audio track (or a fully silent one). Assembly mixes the sound later.
4. **Numbers**: the only numbers an overlay may introduce are the observed.json values used above — `1`
   (`dup_groups`, C1 caption) and the digits of the run id (`manual__2026-11-23T01:00:57.988475+00:00`, C2
   caption line 2). Every caption number comes from the observed.json above — never from the storyboard. Never
   caption the bucket header totals (`113.8 MiB` / `2734 Objects`) as dataset counts. If a needed key were
   missing from observed.json you would stop and report the key name (none is missing: `dup_groups` and
   `run_id` are both present).
5. **QA flags to honor** (carried from the capture QA):
   - The run is FINISHED (5/5 green, Success badge) — no in-progress spinners on camera; overlays must not
     imply a live/in-flight run.
   - C1b is a **static hold** (log pre-scrolled to the bottom, visible lines 16–55) — place the C1b callout
     against the rendered lines without tracking; keep the whole fastdup summary block legible.
   - C2 is a **static object view** (click row → Object Info → Actions > Preview at the end) — callout against
     the object row, appearing while the row + Object Info are in frame.
   - C3: top scroll → one smooth scroll ~21.1–23.3 s → hold on page 3 from ~23.3 s — the C3 caption/chip may
     appear from the shot start (18.53 s); the overlay must not obscure the page-3 title or the
     `group 828: 2 images` line during the hold.
   - C3 pages are canvas-rendered — verify by pixels/geometry. No in-frame internal hostnames (verified false
     by capture: the `airflow-worker:8793` log line is scrolled out of frame).
   - Never caption or imply training/eval/URL/filtering content — segment C is dedup + report only.

## Build, check, render

1. `npx hyperframes check` in `video/segment-c/` — must pass.
2. **Snapshot review**: render a preview, extract frames across the timeline (at minimum around t=0/3.5/9/18.5/
   21/24/27 s), and verify (a) every overlay is placed on the intended element at the intended time, (b) no
   overlay covers on-screen text (esp. the fastdup summary block in C1b, the object row/Object Info in C2, the
   page-3 title + group line in C3), (c) captions are legible over the UI. Fix and re-check before the delivery
   render.
3. Delivery render: `npx hyperframes render --quality delivery -o video/segment-c/renders/segment-c.mp4`
4. **Never commit the render** (`video/segment-c/renders/` stays out of git). Commit the HyperFrames project
   (source clip reference, composition config, observed.json) to branch `factory/t_61fa2737/video-3`.

## Acceptance (report each, with evidence)

- Output: 1920×1080 @ 30 fps, H.264 MP4, length 27.70 s (±1 frame), ≤ 50 MB, no audio (or silent) — quote the
  ffprobe spec line.
- Overlay map: per-shot one-line status (chips / captions / callouts placed as specified; snapshot-review
  outcome).
- Numbers: confirm the only on-screen numbers introduced by overlays are `1` (dup groups, C1) and the run id
  `manual__2026-11-23T01:00:57.988475+00:00` (C2 caption line 2), both sourced from observed.json.
- sha256 of the rendered MP4 + branch tip SHA.
- Anything different from this spec (placement compromises, timing).

End your final message with: (a) per-shot overlay status, (b) the filled values used, (c) ffprobe + sha256 lines,
(d) branch tip SHA of `factory/t_61fa2737/video-3`.

````

## Result (final output, verdict: none)

````
Segment C is composed and rendered. The output is a silent MP4 of 27.70 s and 831 frames, with the source clip underneath left untouched. `hyperframes check` passes (`ok: true`). The snapshot review was clean, and I compared the delivery render with it frame by frame at 6, 15 and 24 s. The project is committed to `factory/t_61fa2737/video-3`; I committed it locally but have not pushed it.

**Where this differs from the spec:**
- **Caption bar position:** it moves per shot instead of sitting as one centred bar. In C1b the log runs down to y≈1046, so a centred bar would have covered log lines 46–55, which hold the fastdup summary and the EMBED OK line. So each shot's caption sits at the bottom of the frame over empty UI:
  - C1: over the left Grid panel.
  - C2: over the empty object list, left of the Object Info panel.
  - C3: in the dialog's left margin, about 50 px clear of the report pages.
- **Small type warnings:** `check` warns that the chips (20 px) and callout labels (18 px) are below its 28 px reading size. I kept them small because the spec asks for small chips and labels. The captions are 27–30 px.
- **Other `check` warning:** it also flags the video as having no sound, which is what the spec requires.
- **Real cut times** (measured from frame differences) match `observed.json`: 3.533 s, 9.800 s and 18.533 s. The C3 scroll actually ends at about 22.90 s rather than 23.3 s; nothing depends on that, because C3 has no callout.
- **Source clip not committed:** `assets/` is git-ignored, as in the segment-D project. `SOURCE.md` gives the path and sha256 to copy it from, and `observed.json` is committed byte-identical (sha256 `b134b92a…b847`).
- **Studio preview skipped:** this was an unattended run, so I didn't open the HyperFrames preview before the delivery render. You can keep editing the project in the HyperFrames desktop app.

**(a) Per-shot overlay status**
- **C1 (0–9.8 s):**
  - Chip `C1 · Deduplicate` at top right, clear of the action icons.
  - Caption `1 near-dup group`.
  - Callout (4.1–9.7 s): a 2 px box drawn in the gaps between lines 53, 54 and 55, so it touches no text, around `EMBED OK: 1000 images, 1 dup groups`. Its label "Duplicate groups" sits in the empty area to the right.
  - The summary block (2.54 / 1000 / 69 / dim=576 / PDF published) stays fully legible, and nothing suggests the run is still in progress.
- **C2 (9.8–18.53 s):**
  - Chip `C2 · Report in MinIO` in the top bar.
  - Two-line caption with the report path.
  - Callout (12.8–18.35 s, i.e. after the row click opens the Object Info panel): a box around the `voc12_embed_report.pdf` name cell, with the label "Report PDF" below it. Last Modified, Size and the Object Info values are not covered.
  - The bucket totals are never captioned.
- **C3 (18.53–27.7 s):**
  - Chip `C3 · Dedup report` in the dialog header.
  - Caption `voc12_embed_report.pdf · dup groups`.
  - No callout. The page-3 title and the `group 828: 2 images` line stay clear throughout the hold.

**(b) Filled values used**
- **Placeholders:**
  - `{n_dup_groups}` → `dup_groups.value` = **1**, rendered singular: "1 near-dup group".
  - `{run_id}` → `run_id.value` = **`manual__2026-11-23T01:00:57.988475+00:00`**.
- **C2 caption:** line 1 `analysis/`; line 2 `manual__2026-11-23T01:00:57.988475+00:00/voc12_embed_report.pdf`.
- **Numbers:** the overlays add no numbers other than the `1` and the run id, both taken from `observed.json`. The callout labels contain no numbers.

**(c) Output spec and hash**
- **ffprobe:** `stream|index=0|codec_name=h264|profile=High|codec_type=video|width=1920|height=1080|pix_fmt=yuv420p|r_frame_rate=30/1|duration=27.700000|nb_frames=831` and `format|duration=27.700000|size=1860410`.
- **Audio and size:** there is no audio stream, and the file is 1.86 MB, well under the 50 MB limit.
- **sha256 of the render:** `0bf35a0b9aeb9a60d90483ee143a75f2ca55c4bcd1499edc444d1577d310ad83  video/segment-c/renders/segment-c.mp4`. The render is not committed.
- **Base clip sha256 (unchanged):** `8810b1eb14a770bb3f61e238e2783511664957ad9a7ef4d2417a60cdf45d1e0f`.

**(d) Branch tip**
- `factory/t_61fa2737/video-3` @ **`4466ff3d422bb62357a5310f3445516338bca433`**.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/claude",
  "artifacts": [
    {
      "attachable": true,
      "path": "video/segment-c/assets/segment-c.mp4",
      "sha256": "8810b1eb14a770bb3f61e238e2783511664957ad9a7ef4d2417a60cdf45d1e0f",
      "size": 1104897,
      "stored": "/srv/factory-artifacts/t_61fa2737/video-3/video/segment-c/assets/segment-c.mp4"
    },
    {
      "attachable": true,
      "path": "video/segment-c/renders/segment-c.mp4",
      "sha256": "0bf35a0b9aeb9a60d90483ee143a75f2ca55c4bcd1499edc444d1577d310ad83",
      "size": 1860410,
      "stored": "/srv/factory-artifacts/t_61fa2737/video-3/video/segment-c/renders/segment-c.mp4"
    }
  ],
  "base_ref": "HEAD",
  "base_sha": "c67e84814f84aef441d624115e847f0646c9ddb6",
  "binary": "/home/dev-runner/.local/bin/claude",
  "branch": "factory/t_61fa2737/video-3",
  "executor": {
    "image": "localhost/factory-media@sha256:5f4bca470357e918a7cf7b21eb8f12a5d580369f68013007b72aeeff13bf0e4c",
    "isolation": "container",
    "key": "sandbox-media",
    "kind": "podman",
    "limits": {
      "cpus": "8",
      "memory": "16g",
      "pids": 8192,
      "shm": "2g"
    },
    "services": {
      "egress-proxy": {
        "port": 8889
      }
    },
    "via": "function_default"
  },
  "exit_file": "/srv/software-factory/.dispatch/t_61fa2737--video-3.exit",
  "function": "video_production",
  "function_class": "work",
  "harness": "claude-video",
  "home_seed": [
    ".claude/settings.json",
    ".claude/plugins",
    ".claude.json",
    ".claude/skills/hyperframes",
    ".claude/skills/hyperframes-cli",
    ".claude/skills/hyperframes-registry"
  ],
  "inputs": [
    {
      "dst": "/inputs/artifacts/t_13de095d/capture-4",
      "src": "/srv/factory-artifacts/t_13de095d/capture-4"
    }
  ],
  "install_roots": [
    "/home/dev-runner/.npm-global",
    "/home/dev-runner/.local"
  ],
  "job_dir": "/srv/factory-jobs/t_61fa2737--video-3",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_61fa2737--video-3.md",
  "prompt_sha256_prefix": "825ca3566c7f8d2d",
  "resolved_via": "function_default",
  "result": {
    "sha256": "4816e019b580f6123e85615e6a3c756d53119911e381ce502efb4e8cc3e0607c",
    "stored": "/srv/factory-artifacts/t_61fa2737/video-3/result.md",
    "truncated": false,
    "verdict": null
  },
  "resume_session": null,
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN"
  ],
  "spec_sha256": "996bd8bc6f7bc01ffadb8be3578d969c0f448a51a1a4d3488d6762c294fbc042",
  "staging": null,
  "stream": null,
  "ticket": "t_61fa2737",
  "transcript": "/srv/factory-jobs/t_61fa2737--video-3/transcript.log",
  "transcript_sha256": "f076dc6914b081f716750343ce422aa9fa45a50e485a007b188f2d2fda8e884d",
  "window": "video-3",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
