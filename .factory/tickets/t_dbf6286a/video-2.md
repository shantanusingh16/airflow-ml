# t_dbf6286a / video-2

## Prompt as dispatched

````
---
factory: {base: HEAD, inputs: [artifacts/t_8a350dbc/capture-3c]}
---

# Task: voc12_demo UX demo video — segment B compose (VERIFY + INGEST)

Compose **segment B** of the voc12_demo UX demo: add **HyperFrames overlays/captions** to the already-captured,
QA-approved clip. You deliver **one silent MP4** — VO and music are mixed later at assembly. All inputs are
artifacts (mounted read-only under `/inputs`); there is **no staging access** and no staging is needed.

## Inputs (mounted)

- Source clip: `/inputs/artifacts/t_8a350dbc/capture-3c/out/segment-b.mp4`
  — H.264, 1920×1080 @ 30 fps, 30.067 s, 1,077,128 B, sha256
  `9b97cdc42c8cf24b38bdd9763d3ff273208f3e27371c89b558d78e869374b832` (QA-verified; do not alter it).
  NOTE: the compose card header says "capture-3", but the capture went through operator re-captures; the
  approved window is **capture-3c** (capture-3/ and capture-3b/ hold only partial result.md stubs from stopped
  runs). Use the capture-3c mount only.
- `observed.json` — the single source of truth for every number in this window. NOTE: this window's artifact
  directory contains only the MP4, so the byte-identical observed.json (sha256
  `3358def03b3541ef82ec20813f876190bf93ac2c2ff83054c3d460020dd41f95`, byte-identical to the copy committed on
  `factory/t_8a350dbc/capture-3c` and to the copy attached to capture card t_8a350dbc) is inlined below. Write it
  into the build folder verbatim and treat it as the ONLY numeric source:

```json
{
  "dag_id": "voc12_demo",
  "run_id": "manual__2026-11-23T01:00:57.988475+00:00",
  "run_state": "Success",
  "run_duration": "00:17:02",
  "grid_task_states": {
    "upload_voc12": "success",
    "verify_upload": "success",
    "ingest_voc12": "success",
    "embed_fastdup": "success",
    "cluster_split": "success"
  },
  "objects_total": 2001,
  "jpegs": 1000,
  "xmls": 1000,
  "trainval_image_refs": 1000,
  "images_verified": 1000,
  "annotations_verified": 1000,
  "verify_prefix": "s3://ml-artifacts/datasets/voc12/VOC2012/",
  "annotation_files_found": 1000,
  "annotation_prefix": "s3://ml-artifacts/datasets/voc12/VOC2012/Annotations/",
  "images_ingested": 1000,
  "boxes_ingested": 1628,
  "deeplake_dataset": "s3://ml-artifacts/deeplake/voc12",
  "deeplake_commit": "firstdbf9474",
  "clip": "/work/out/segment-b.mp4",
  "clip_seconds": 30.09,
  "where": {
    "objects_total": "B2: verify_upload log, Pre Execute L11 \"datasets/voc12/VOC2012/: 2001 objects, 1000 JPEGs, 1000 XMLs\"",
    "jpegs": "B2: same line (L11)",
    "xmls": "B2: same line (L11)",
    "trainval_image_refs": "B2: Pre Execute L12 \"trainval.txt: 1000 image refs\"",
    "images_verified": "B2: Pre Execute L13 \"UPLOAD OK: 1000 images + 1000 annotations verified in s3://ml-artifacts/datasets/voc12/VOC2012/\"",
    "annotations_verified": "B2: L13 (same line)",
    "verify_prefix": "B2: L13 (s3://ml-artifacts/datasets/voc12/VOC2012/)",
    "annotation_files_found": "B3b: ingest_voc12 log, Pre Execute L13 \"found 1000 annotation files under s3://…/Annotations/\"",
    "annotation_prefix": "B3b: L13 (s3://ml-artifacts/datasets/voc12/VOC2012/Annotations/)",
    "images_ingested": "B3b: Pre Execute L17 \"INGEST OK: 1000 images, 1628 boxes → s3://ml-artifacts/deeplake/voc12 (commit firstdbf9474)\"",
    "boxes_ingested": "B3b: L17 (same line)",
    "deeplake_dataset": "B3b: L14 \"s3://ml-artifacts/deeplake/voc12 loaded successfully.\" (also L17)",
    "deeplake_commit": "B3b: L15 \"DeepLake commit firstdbf9474 …\" and L17 \"(commit firstdbf9474)\"",
    "run_state": "B1/B3a: DAG header \"Latest Run 2026-11-23 01:00:57\" with green success check; grid run column with 5 green success cells; B1 hover tooltip \"State: Success\" (task-level)",
    "run_duration": "B1/B3a: grid duration axis label \"00:17:02\" at the top of the run bar",
    "run_id": "B1: verify_upload cell hover tooltip \"Run ID: manual__2026-11-23T01:00:57.988475+00:00\" (also B3a ingest_voc12 tooltip)",
    "grid_task_states": "B1/B3a: grid run column, one green success badge per task row (upload_voc12, verify_upload, ingest_voc12, embed_fastdup, cluster_split); state read from each cell tooltip \"State: Success\""
  },
  "notes": {
    "grid": "Grid rendered on /dags/voc12_demo after 2.5s; B1 cursor on the verify_upload cell (tooltip State: Success), B3a cursor on the ingest_voc12 cell. The documented Grid WS outage did not reproduce: grid data loaded via the REST /ui/grid/* endpoints.",
    "scroll": "No scrolling was needed or performed: on load (after expanding the Pre Execute section) the required lines were already in frame for both log shots; both holds are fully static.",
    "source_url_line": "The lazily-rendered source-URL line carrying the internal hostname (http://airflow-worker:8793/log/…) never appeared in either log view: absent after the 12 s lazy-render window in the off-take probe and re-checked at settle and hold end on camera. Nothing to cover.",
    "lazy_check": "Line positions were verified twice per log shot (at hold start and hold end) via bounding boxes.",
    "timeline": "Shot boundaries from the capture log + ffmpeg freezedetect (static spans 9.13-17.60 s and 24.37-30.07 s are the B2/B3b log holds; no UI scrolling inside any hold)."
  },
  "timeline_s": {
    "B1_grid_verify_upload": [
      0.0,
      7.6
    ],
    "B1_to_B2_transition": [
      7.6,
      9.1
    ],
    "B2_verify_log_hold": [
      9.1,
      17.6
    ],
    "B3a_grid_ingest_voc12": [
      17.6,
      22.9
    ],
    "B3_to_log_transition": [
      22.9,
      24.4
    ],
    "B3b_ingest_log_hold": [
      24.4,
      30.07
    ]
  }
}
```

Placeholder mapping (compose contract, v2): `{n_verified}` → `images_verified` = 1000; `{n_ingested}` →
`images_ingested` = 1000. Both are grounded on camera (see below). No other placeholders appear in segment B.

## What the clip contains (QA-verified, presentation order B1 → B2 → B3)

| Shot | Time | On screen |
|------|------|-----------|
| B1 | 0–7.6 s | Airflow **Grid view** (`/dags/voc12_demo`; Airflow 3: per-run columns with state badges; task names in a left panel: upload_voc12, verify_upload, ingest_voc12, embed_fastdup, cluster_split). The run column (label = manual-run icon + start time `2026-11-23 01:00:57` — the raw `manual__…` id is NOT on screen; duration axis label `00:17:02`) shows **all 5 task cells already green** (finished run). Cursor is on the **verify_upload** cell; at ~4.3 s the cell hover tooltip is visible (Task ID: verify_upload, State: Success, Run ID: manual__2026-11-23T01:00:57.988475+00:00). No hostnames, no VOC pixels. |
| B2 | 9.1–17.6 s | `verify_upload` task log (Logs tab, Pre Execute section), **fully static hold**, lines 11–13 in frame: `datasets/voc12/VOC2012/: 2001 objects, 1000 JPEGs, 1000 XMLs` / `trainval.txt: 1000 image refs` / `UPLOAD OK: 1000 images + 1000 annotations verified in s3://ml-artifacts/datasets/voc12/VOC2012/`. The `Log message source details` row is collapsed — the internal-hostname source-URL line never rendered (QA-verified across the whole hold). Pointer parked off-frame. No hostnames, no VOC pixels. |
| B3a | 17.6–22.9 s | Back on Grid; cursor on the **ingest_voc12** cell (green) — at ~21 s the cell tooltip is visible (`Task ID: ingest_voc12 / State: Success / Run ID: manual__2026-11-23T01:00:57.988475+00:00 / Duration: 00:00:08`), then the cell is clicked and opens its task log. |
| B3b | 24.4–30.07 s | `ingest_voc12` task log (Logs tab, Pre Execute), **fully static hold**, lines 13–17 in frame: `found 1000 annotation files under s3://ml-artifacts/datasets/voc12/VOC2012/Annotations/` / `s3://ml-artifacts/deeplake/voc12 loaded successfully.` / `DeepLake commit firstdbf9474 …` / `INGEST OK: 1000 images, 1628 boxes → s3://ml-artifacts/deeplake/voc12 (commit firstdbf9474)`. Cursor visible. No VOC pixels, no hostnames. |

Timing: boundaries are `timeline_s` from observed.json (B1 0–7.6, B1→B2 transition 7.6–9.1, B2 hold 9.1–17.6,
B3a 17.6–22.9, B3→log transition 22.9–24.4, B3b hold 24.4–30.07; total 30.07 s). Extract sample frames around
the two cuts to pin the exact boundaries and time the overlays to them.

## Overlays to build (HyperFrames, on the captured clip only)

Use the **hyperframes skill**. Build the HyperFrames project in folder **`video/segment-b/`** at the repo root
(source clip + observed.json copied into that folder for the build).

Per shot, exactly these overlay elements:

1. **Title chip** (small chip, top corner, constant for the shot):
   - B1 (0–9.1 s): `B1 · Verify`
   - B2 (9.1–17.6 s): `B2 · Verify log`
   - B3 (17.6–30.07 s): `B3 · Ingest`
2. **Caption bar** (bottom of frame, always on for the whole segment, one line per shot — v2 copy verbatim,
   filled STRICTLY from observed.json):
   - B1: `verify_upload ✓` (no number in this caption)
   - B2: `1000 images verified` (filled: `{n_verified}` → `images_verified` = 1000; grounded in on-screen L13
     `UPLOAD OK: 1000 images + 1000 annotations verified`)
   - B3: `ingest_voc12: 1000 images` (filled: `{n_ingested}` → `images_ingested` = 1000; grounded in on-screen L17
     `INGEST OK: 1000 images, 1628 boxes`)
   The v2 `{n_pairs}` line was dropped — B2 gets exactly the single caption line above. The on-screen
   `2001 objects` line stays in frame as UI context (it is on camera, not added by overlays).
3. **Callout boxes** (thin border + small label, pointer to the element; appear only while the element is in
   frame; must not cover any on-screen text). Time each callout to the actual frames (extract sample frames per
   shot to place them):
   - B1: the green **verify_upload** cell in the run column (the already-green cell the shot holds on).
   - B2: the log count lines L11–L13 — the `2001 objects, 1000 JPEGs, 1000 XMLs` line, the `trainval.txt: 1000
     image refs` line, and the `UPLOAD OK: 1000 images + 1000 annotations verified` line. Keep all three lines
     fully legible.
   - B3a: the green **ingest_voc12** cell (while the cell / tooltip is in frame).
   - B3b: the `INGEST OK: 1000 images, 1628 boxes` line (and optionally the `deeplake/voc12 loaded successfully`
     line). Do NOT cover the `DeepLake commit firstdbf9474` line.
   Never render the raw `manual__…` run id as overlay text (it is on-screen in the UI/tooltips themselves — that
   is fine — but the overlays must not add it).

## Hard rules

1. **Never re-render, speed-change, crop the content area, or alter the captured UI.** The base video is the
   source clip untouched; overlays are composited on top only. Output length = input length (30.067 s).
2. **No external images or footage** of any kind — overlays are text/chips/boxes only. Licensing: no full-screen
   VOC images may appear (source is QA-checked: pure UI + log text, no VOC pixels); overlays must not introduce
   image content.
3. **Silent segment** — no VO, no music, no audio track (or a fully silent one). Assembly mixes the sound later.
4. **Numbers**: the only numbers an overlay may introduce are the two `1000` values from observed.json
   (`images_verified` in B2, `images_ingested` in B3). All other numbers (2001 objects, 1000 XMLs, 1000 trainval
   refs, 1628 boxes, 00:17:02) are on-screen in the UI/logs — overlays must not add them. Every caption number
   comes from the observed.json above — never from the storyboard. If a needed key were missing from
   observed.json you would stop and report the key name (none is missing).
5. **Never caption or imply training/eval content** — segment B is verify + ingest only (dataset validation and
   DeepLake load). No URL-acquisition or annotation-filtering content either.
6. **QA flags to honor** (carried from the capture review):
   - B2 (9.1–17.6 s) and B3b (24.4–30.07 s) are **fully static holds** (QA-verified: no in-shot scrolling) —
     callouts can be placed statically, no tracking.
   - B1 frames are pixel-static except the hover tooltip at ~4.3 s.
   - The lazily-rendered source-URL line (internal hostname) **never appeared** in either log view (QA-verified
     across the 12 s lazy-render window and at hold end) — **no hostname cover bar is needed** (unlike segment
     A).
   - The pointer is **off-frame during the B2 hold** — do not call out the cursor in B2; it is visible in B1 and
     B3b.
   - The Grid renders as **per-run columns with state badges** (Airflow 3), not a day×task matrix; the run row
     label is icon + start time — never render the raw `manual__…` run id as overlay text.
   - The green cells are **already green** (finished run) — the B1 callout must not depict any state transition
     ("turning green" animation); v2 spec is "hold on the already-green cell".

## Build, check, render

1. `npx hyperframes check` in `video/segment-b/` — must pass.
2. **Snapshot review**: render a preview, extract frames across the timeline, and verify (a) every overlay is
   placed on the intended element at the intended time, (b) no overlay covers on-screen text (esp. L11–L13 in B2
   and L13–L17 in B3b, and the green cell + tooltip in B1/B3a), (c) captions are legible over the near-white
   Airflow UI. Fix and re-check before the delivery render.
3. Delivery render: `npx hyperframes render --quality delivery -o video/segment-b/renders/segment-b.mp4`
4. **Never commit the render** (`video/segment-b/renders/` stays out of git). Commit the HyperFrames project
   (source clip reference, composition config, observed.json) to branch `factory/t_dbf6286a/video-1`.

## Acceptance (report each, with evidence)

- Output: 1920×1080 @ 30 fps, H.264 MP4, length 30.067 s (±1 frame), ≤ 50 MB, no audio (or silent) — quote the
  ffprobe spec line.
- Overlay map: per-shot one-line status (chips / captions / callouts placed as specified; snapshot-review
  outcome).
- Numbers: confirm the only on-screen numbers introduced by overlays are the two `1000` values (B2 and B3
  captions), both sourced from observed.json.
- sha256 of the rendered MP4 + branch tip SHA.
- Anything different from this spec (placement compromises, timing).

End your final message with: (a) per-shot overlay status, (b) the filled values used, (c) ffprobe + sha256 lines,
(d) branch tip SHA of `factory/t_dbf6286a/video-1`.

````

## Result (final output, verdict: none)

````
Segment B is rendered and the project is committed. The render matches the spec, with one exception: I committed to **`factory/t_dbf6286a/video-2`**, not `video-1` as the card says. This session runs on `video-2`, and the earlier `video-1` run died on API 502 errors, leaving that branch with only its record commit. I didn't push, and I didn't write to the `video-1` branch. If it has to land on `video-1`, it's a single commit to cherry-pick.

**Output:** `video/segment-b/renders/segment-b.mp4`, 2,275,189 B (about 2.2 MB). It is ignored by git and not committed. `npx hyperframes check` passes with 0 errors. The 4 warnings are expected:
- "film is silent", which the spec requires.
- Small text on the 18 px callout labels. They have to stay small to fit beside the 13 px log lines.

**Verification:**
- **Base video untouched:** all 902 frames line up with the source. In an area with no overlays, the worst difference is 2.1/255 (compression noise), so no frames are frozen, shifted, cropped or re-timed. I checked this because the source has keyframes up to 8 s apart.
- **No text covered:** on every protected area, 0 pixels changed: B2 lines L10–L13 and "Post Execute", B3b lines L14–L18 (including the `DeepLake commit firstdbf9474` line), all grid cells, both tooltips, and the `00:17:02`/`00:08:31` axis labels.
- **Snapshot review:** I checked frames at 15 points across the timeline, plus zoomed crops of each callout.

**Cut points measured from the frames:**
- B1 grid ends with a hard cut at 7.567 s; white/loading frames run to 9.133 s.
- The B2 log is static from 9.133 to 17.6 s.
- The B3a grid has fully rendered by 18.6 s, and the ingest tooltip is on screen 19.8–22.867 s.
- The B3b log is static from 24.367 s.

**Differences from the spec:**
- **Slight colour shift.** The source is tagged BT.601 and the HyperFrames render comes out BT.709. White is exact; the saturated sidebar blue moves by up to about 6/255. Fixing it would mean re-encoding the source, which the spec forbids, so I left it.
- **Chip timing.** The `B1 · Verify` chip stays up through the white/loading frames (7.6–9.1 s) before the B2 log appears, because the spec sets the chip boundaries there.
- **B1 callout and cursor.** From 4.33 s the cursor ring touches the right edge of the verify_upload box. It's the cursor, not text.
- **Task names in labels.** The callout labels contain the task names `verify_upload` and `ingest_voc12`. The "12" in `ingest_voc12` is part of the name (as in the spec's own B3 caption), not a new number.
- **Preview step skipped.** I didn't open the interactive preview before the delivery render because this session has no display. The project can still be opened and edited in the HyperFrames desktop app.
- The optional callout on the `deeplake/voc12 loaded successfully` line was not added.

**(a) Per-shot overlay status**
- **B1 (0–9.1 s):** chip `B1 · Verify`; caption `verify_upload ✓`. A box sits on the already-green verify_upload cell from 0.5 to 7.45 s, labelled "verify_upload · success". It has no state-change animation and is gone before the 7.567 s cut. Review passed.
- **B2 (9.1–17.6 s):** chip `B2 · Verify log`; caption `1000 images verified`. A box surrounds L11–L13 from 9.4 to 17.45 s, labelled "verify_upload counts" in the empty space to the right of L13. The borders run only through the 6 px gaps between lines, all three lines are fully legible, and the cursor isn't called out. Review passed.
- **B3 (17.6–30.067 s):** chip `B3 · Ingest`; caption `ingest_voc12: 1000 images`. For B3a, a box sits on the green ingest_voc12 cell from 18.7 to 22.75 s and doesn't touch the tooltip. For B3b, a box surrounds the L17 `INGEST OK` line from 24.5 s to the end, labelled "ingest result → DeepLake". Review passed.
- No overlay shows the raw `manual__…` run id, there is no hostname cover bar, and nothing refers to training or eval.

**(b) Filled values used** (from observed.json, sha256 `3358def03b3541ef82ec20813f876190bf93ac2c2ff83054c3d460020dd41f95`, byte-identical to the copy on the capture-3c branch)
- `{n_verified}` → `images_verified` = **1000** (B2 caption)
- `{n_ingested}` → `images_ingested` = **1000** (B3 caption)
- These are the only numbers the overlays add.

**(c) ffprobe + sha256**
```
stream|index=0|codec_name=h264|profile=High|codec_type=video|width=1920|height=1080|pix_fmt=yuv420p|r_frame_rate=30/1|avg_frame_rate=30/1|duration=30.066667|nb_frames=902
format|duration=30.066667|size=2275189        (audio streams: 0)
bff3008c40adcd14db6b9714fd981872261b3ff7928e8e336340daa5b05a1f25  renders/segment-b.mp4
```

**(d) Branch tip:** the card asks for `factory/t_dbf6286a/video-1`. The commit is on **`factory/t_dbf6286a/video-2`** at **`a9bac109a047a218c0a4cd115373f26f0a4fcd20`**, not pushed.
````

## Dispatch record

```json
{
  "argv0": "/home/dev-runner/.local/bin/claude",
  "artifacts": [],
  "base_ref": "HEAD",
  "base_sha": "c67e84814f84aef441d624115e847f0646c9ddb6",
  "binary": "/home/dev-runner/.local/bin/claude",
  "branch": "factory/t_dbf6286a/video-2",
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
  "exit_file": "/srv/software-factory/.dispatch/t_dbf6286a--video-2.exit",
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
      "dst": "/inputs/artifacts/t_8a350dbc/capture-3c",
      "src": "/srv/factory-artifacts/t_8a350dbc/capture-3c"
    }
  ],
  "install_roots": [
    "/home/dev-runner/.npm-global",
    "/home/dev-runner/.local"
  ],
  "job_dir": "/srv/factory-jobs/t_dbf6286a--video-2",
  "mode": "print",
  "project": "airflow-ml",
  "project_real": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "prompt_file": "/srv/software-factory/.dispatch/t_dbf6286a--video-2.md",
  "prompt_sha256_prefix": "289755f24fd4b626",
  "resolved_via": "function_default",
  "result": {
    "sha256": "35bd15b0a131e36ab0b13c3eb8a3b8713ca99a5a715f1a599eb65596d5c561d1",
    "stored": "/srv/factory-artifacts/t_dbf6286a/video-2/result.md",
    "truncated": false,
    "verdict": null
  },
  "resume_session": null,
  "routing_sha256_prefix": "a1ce7f45d24409f3",
  "secrets": [
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN"
  ],
  "spec_sha256": "2de61470222305ca0c2441447c4ee90c71fad91cc021cc266b8954f2aced36ab",
  "staging": null,
  "stream": null,
  "ticket": "t_dbf6286a",
  "transcript": "/srv/factory-jobs/t_dbf6286a--video-2/transcript.log",
  "transcript_sha256": "5717d645df0b699fe6f66e537945a695aead19b741e431ed2a8c92e82c32162a",
  "window": "video-2",
  "workdir": "/run/media/shantanu/Volume/Projects/airflow-ml",
  "workdir_rel": "."
}
```
